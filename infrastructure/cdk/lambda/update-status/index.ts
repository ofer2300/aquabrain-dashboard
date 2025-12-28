/**
 * AquaSkill Update Status Lambda
 * Called by Bedrock Agent Action Group to update task status
 */
import { DynamoDBClient, UpdateItemCommand } from '@aws-sdk/client-dynamodb';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

const dynamodb = new DynamoDBClient({});
const s3 = new S3Client({});

interface BedrockAgentEvent {
  messageVersion: string;
  agent: {
    name: string;
    id: string;
    alias: string;
    version: string;
  };
  actionGroup: string;
  apiPath: string;
  httpMethod: string;
  parameters: Array<{
    name: string;
    type: string;
    value: string;
  }>;
  requestBody?: {
    content: {
      'application/json': {
        properties: Record<string, { value: string }>;
      };
    };
  };
}

interface BedrockAgentResponse {
  messageVersion: string;
  response: {
    actionGroup: string;
    apiPath: string;
    httpMethod: string;
    httpStatusCode: number;
    responseBody: {
      'application/json': {
        body: string;
      };
    };
  };
}

function buildResponse(
  event: BedrockAgentEvent,
  statusCode: number,
  body: Record<string, unknown>
): BedrockAgentResponse {
  return {
    messageVersion: '1.0',
    response: {
      actionGroup: event.actionGroup,
      apiPath: event.apiPath,
      httpMethod: event.httpMethod,
      httpStatusCode: statusCode,
      responseBody: {
        'application/json': {
          body: JSON.stringify(body),
        },
      },
    },
  };
}

export const handler = async (event: BedrockAgentEvent): Promise<BedrockAgentResponse> => {
  console.log('Bedrock Agent Event:', JSON.stringify(event, null, 2));

  const apiPath = event.apiPath;
  const parameters: Record<string, string> = {};

  // Extract parameters
  for (const param of event.parameters || []) {
    parameters[param.name] = param.value;
  }

  try {
    if (apiPath === '/update-status') {
      return await handleUpdateStatus(event, parameters);
    } else if (apiPath === '/save-artifact') {
      return await handleSaveArtifact(event);
    } else {
      return buildResponse(event, 400, { error: `Unknown API path: ${apiPath}` });
    }
  } catch (error) {
    console.error('Handler error:', error);
    return buildResponse(event, 500, {
      error: 'Internal error',
      details: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

async function handleUpdateStatus(
  event: BedrockAgentEvent,
  params: Record<string, string>
): Promise<BedrockAgentResponse> {
  const { task_id, status, traffic_light, current_step, total_steps, pdf_url, message } = params;

  if (!task_id) {
    return buildResponse(event, 400, { error: 'Missing required parameter: task_id' });
  }

  const updateExpression: string[] = ['#updated_at = :updated_at'];
  const expressionAttributeNames: Record<string, string> = {
    '#updated_at': 'updated_at',
  };
  const expressionAttributeValues: Record<string, { S?: string; N?: string }> = {
    ':updated_at': { S: new Date().toISOString() },
  };

  if (status) {
    updateExpression.push('#status = :status');
    expressionAttributeNames['#status'] = 'status';
    expressionAttributeValues[':status'] = { S: status };
  }

  if (traffic_light) {
    updateExpression.push('traffic_light = :traffic_light');
    expressionAttributeValues[':traffic_light'] = { S: traffic_light };
  }

  if (current_step) {
    updateExpression.push('current_step = :current_step');
    expressionAttributeValues[':current_step'] = { N: current_step };
  }

  if (total_steps) {
    updateExpression.push('total_steps = :total_steps');
    expressionAttributeValues[':total_steps'] = { N: total_steps };
  }

  if (pdf_url) {
    updateExpression.push('pdf_url = :pdf_url');
    expressionAttributeValues[':pdf_url'] = { S: pdf_url };
  }

  if (message) {
    updateExpression.push('#message = :message');
    expressionAttributeNames['#message'] = 'message';
    expressionAttributeValues[':message'] = { S: message };
  }

  await dynamodb.send(new UpdateItemCommand({
    TableName: process.env.TABLE_NAME!,
    Key: {
      task_id: { S: task_id },
    },
    UpdateExpression: `SET ${updateExpression.join(', ')}`,
    ExpressionAttributeNames: expressionAttributeNames,
    ExpressionAttributeValues: expressionAttributeValues,
  }));

  return buildResponse(event, 200, {
    success: true,
    task_id,
    status: status || 'unchanged',
    updated_at: new Date().toISOString(),
  });
}

async function handleSaveArtifact(event: BedrockAgentEvent): Promise<BedrockAgentResponse> {
  const body = event.requestBody?.content?.['application/json']?.properties;

  if (!body) {
    return buildResponse(event, 400, { error: 'Missing request body' });
  }

  const taskId = body.task_id?.value;
  const artifactType = body.artifact_type?.value;
  const content = body.content?.value;
  const filename = body.filename?.value;

  if (!taskId || !artifactType || !content) {
    return buildResponse(event, 400, {
      error: 'Missing required fields: task_id, artifact_type, content',
    });
  }

  const key = `${taskId}/${filename || `artifact.${artifactType}`}`;

  await s3.send(new PutObjectCommand({
    Bucket: process.env.AUDIT_BUCKET!,
    Key: key,
    Body: content,
    ContentType: getContentType(artifactType),
    Metadata: {
      task_id: taskId,
      artifact_type: artifactType,
      created_at: new Date().toISOString(),
    },
  }));

  const s3Uri = `s3://${process.env.AUDIT_BUCKET}/${key}`;

  // Update DynamoDB with artifact URL
  if (artifactType === 'pdf') {
    await dynamodb.send(new UpdateItemCommand({
      TableName: process.env.TABLE_NAME!,
      Key: { task_id: { S: taskId } },
      UpdateExpression: 'SET pdf_url = :url, #updated_at = :updated_at',
      ExpressionAttributeNames: { '#updated_at': 'updated_at' },
      ExpressionAttributeValues: {
        ':url': { S: s3Uri },
        ':updated_at': { S: new Date().toISOString() },
      },
    }));
  }

  return buildResponse(event, 200, {
    success: true,
    s3_uri: s3Uri,
    artifact_type: artifactType,
  });
}

function getContentType(artifactType: string): string {
  const contentTypes: Record<string, string> = {
    pdf: 'application/pdf',
    json: 'application/json',
    csv: 'text/csv',
    dxf: 'application/dxf',
  };
  return contentTypes[artifactType] || 'application/octet-stream';
}
