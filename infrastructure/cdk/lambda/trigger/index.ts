/**
 * AquaSkill Trigger Lambda
 * Receives API Gateway requests and queues jobs for processing
 */
import { DynamoDBClient, PutItemCommand } from '@aws-sdk/client-dynamodb';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { v4 as uuidv4 } from 'uuid';

const dynamodb = new DynamoDBClient({});
const sqs = new SQSClient({});

interface TriggerRequest {
  project_id: string;
  project_type: 'new_design' | 'renovation' | 'hydraulic_review' | 'compliance_audit';
  hazard_class: 'Light' | 'Ordinary Group 1' | 'Ordinary Group 2' | 'Extra Group 1' | 'Extra Group 2';
  input_files: { s3_uri: string; file_type: string }[];
  building_info?: {
    total_area_sqft: number;
    floors: number;
    ceiling_height_ft: number;
  };
  water_supply?: {
    available_pressure_psi: number;
    available_flow_gpm: number;
  };
  priority?: 'standard' | 'urgent' | 'critical';
}

interface APIGatewayEvent {
  body: string;
  headers: Record<string, string>;
  requestContext: {
    requestId: string;
  };
}

interface APIGatewayResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: string;
}

export const handler = async (event: APIGatewayEvent): Promise<APIGatewayResponse> => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Content-Type': 'application/json',
  };

  try {
    const request: TriggerRequest = JSON.parse(event.body);
    const taskId = uuidv4();
    const createdAt = new Date().toISOString();
    const ttl = Math.floor(Date.now() / 1000) + (7 * 24 * 60 * 60); // 7 days

    // Validate required fields
    if (!request.project_id || !request.project_type || !request.hazard_class) {
      return {
        statusCode: 400,
        headers: corsHeaders,
        body: JSON.stringify({
          error: 'Missing required fields: project_id, project_type, hazard_class',
        }),
      };
    }

    // Create DynamoDB record
    await dynamodb.send(new PutItemCommand({
      TableName: process.env.TABLE_NAME!,
      Item: {
        task_id: { S: taskId },
        created_at: { S: createdAt },
        project_id: { S: request.project_id },
        project_type: { S: request.project_type },
        hazard_class: { S: request.hazard_class },
        status: { S: 'QUEUED' },
        traffic_light: { S: 'PENDING' },
        current_step: { N: '0' },
        total_steps: { N: '12' },
        input_files: { S: JSON.stringify(request.input_files || []) },
        building_info: { S: JSON.stringify(request.building_info || {}) },
        water_supply: { S: JSON.stringify(request.water_supply || {}) },
        priority: { S: request.priority || 'standard' },
        ttl: { N: ttl.toString() },
      },
    }));

    // Queue the job
    await sqs.send(new SendMessageCommand({
      QueueUrl: process.env.QUEUE_URL!,
      MessageBody: JSON.stringify({
        task_id: taskId,
        project_id: request.project_id,
        project_type: request.project_type,
        hazard_class: request.hazard_class,
        input_files: request.input_files,
        building_info: request.building_info,
        water_supply: request.water_supply,
        priority: request.priority || 'standard',
      }),
      MessageGroupId: request.project_id,
      MessageDeduplicationId: taskId,
    }));

    return {
      statusCode: 200,
      headers: corsHeaders,
      body: JSON.stringify({
        task_id: taskId,
        status: 'QUEUED',
        message: 'Job queued successfully. Poll /status/{task_id} for updates.',
        estimated_completion: '5-10 minutes',
      }),
    };

  } catch (error) {
    console.error('Trigger error:', error);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({
        error: 'Failed to queue job',
        details: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
};
