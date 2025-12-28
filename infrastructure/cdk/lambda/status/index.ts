/**
 * AquaSkill Status Lambda
 * Returns current status of a task for frontend polling
 */
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';

const dynamodb = new DynamoDBClient({});

interface APIGatewayEvent {
  pathParameters: {
    task_id: string;
  };
}

interface APIGatewayResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: string;
}

interface TaskStatus {
  task_id: string;
  project_id: string;
  status: string;
  traffic_light: string;
  current_step: number;
  total_steps: number;
  message?: string;
  pdf_url?: string;
  bom_url?: string;
  created_at: string;
  updated_at?: string;
  errors?: string[];
}

export const handler = async (event: APIGatewayEvent): Promise<APIGatewayResponse> => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Content-Type': 'application/json',
  };

  const taskId = event.pathParameters?.task_id;

  if (!taskId) {
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: 'Missing task_id parameter' }),
    };
  }

  try {
    // Query DynamoDB for the task
    const result = await dynamodb.send(new GetItemCommand({
      TableName: process.env.TABLE_NAME!,
      Key: {
        task_id: { S: taskId },
      },
    }));

    if (!result.Item) {
      return {
        statusCode: 404,
        headers: corsHeaders,
        body: JSON.stringify({ error: 'Task not found' }),
      };
    }

    const item = result.Item;

    const status: TaskStatus = {
      task_id: item.task_id?.S || taskId,
      project_id: item.project_id?.S || '',
      status: item.status?.S || 'UNKNOWN',
      traffic_light: item.traffic_light?.S || 'PENDING',
      current_step: parseInt(item.current_step?.N || '0', 10),
      total_steps: parseInt(item.total_steps?.N || '12', 10),
      created_at: item.created_at?.S || '',
      updated_at: item.updated_at?.S,
      message: item.message?.S,
      pdf_url: item.pdf_url?.S,
      bom_url: item.bom_url?.S,
      errors: item.errors?.S ? JSON.parse(item.errors.S) : undefined,
    };

    // Calculate progress percentage
    const progress = Math.round((status.current_step / status.total_steps) * 100);

    return {
      statusCode: 200,
      headers: corsHeaders,
      body: JSON.stringify({
        ...status,
        progress_percent: progress,
        is_complete: status.status === 'COMPLETED' || status.status === 'FAILED',
      }),
    };

  } catch (error) {
    console.error('Status query error:', error);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({
        error: 'Failed to retrieve status',
        details: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
};
