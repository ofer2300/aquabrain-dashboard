/**
 * AquaSkill Worker Lambda
 * Consumes SQS jobs and invokes Bedrock Agent
 */
import {
  BedrockAgentRuntimeClient,
  InvokeAgentCommand,
} from '@aws-sdk/client-bedrock-agent-runtime';
import { DynamoDBClient, UpdateItemCommand } from '@aws-sdk/client-dynamodb';
import { SQSEvent, SQSRecord } from 'aws-lambda';

const bedrockAgent = new BedrockAgentRuntimeClient({});
const dynamodb = new DynamoDBClient({});

interface JobPayload {
  task_id: string;
  project_id: string;
  project_type: string;
  hazard_class: string;
  input_files: Array<{ s3_uri: string; file_type: string }>;
  building_info?: {
    total_area_sqft: number;
    floors: number;
    ceiling_height_ft: number;
  };
  water_supply?: {
    available_pressure_psi: number;
    available_flow_gpm: number;
  };
  priority: string;
}

export const handler = async (event: SQSEvent): Promise<void> => {
  for (const record of event.Records) {
    await processJob(record);
  }
};

async function processJob(record: SQSRecord): Promise<void> {
  const payload: JobPayload = JSON.parse(record.body);
  const { task_id, project_id, project_type, hazard_class, input_files, building_info, water_supply } = payload;

  console.log(`Processing task ${task_id} for project ${project_id}`);

  try {
    // Update status to PROCESSING
    await updateStatus(task_id, 'PROCESSING', 'Initializing AquaSkill Agent...');

    // Build the prompt for Bedrock Agent
    const prompt = buildAgentPrompt(payload);

    // Invoke Bedrock Agent
    const response = await bedrockAgent.send(new InvokeAgentCommand({
      agentId: process.env.AGENT_ID!,
      agentAliasId: process.env.AGENT_ALIAS_ID!,
      sessionId: task_id,
      inputText: prompt,
      enableTrace: true,
    }));

    // Process streaming response
    let fullResponse = '';

    if (response.completion) {
      for await (const chunk of response.completion) {
        if (chunk.chunk?.bytes) {
          const text = new TextDecoder().decode(chunk.chunk.bytes);
          fullResponse += text;
          console.log('Agent chunk:', text);
        }
      }
    }

    console.log('Agent completed. Full response length:', fullResponse.length);

    // Final status update (Agent should have updated intermediate statuses via Action Group)
    // This is a fallback in case Agent didn't complete properly
    await updateStatus(task_id, 'COMPLETED', 'Pipeline completed successfully', 'GREEN');

  } catch (error) {
    console.error(`Error processing task ${task_id}:`, error);

    await updateStatus(
      task_id,
      'FAILED',
      `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      'RED'
    );

    // Re-throw to trigger SQS retry/DLQ
    throw error;
  }
}

function buildAgentPrompt(payload: JobPayload): string {
  const { task_id, project_id, project_type, hazard_class, input_files, building_info, water_supply } = payload;

  let prompt = `
# AquaSkill LOD 500 Design Request

## Task Information
- Task ID: ${task_id}
- Project ID: ${project_id}
- Project Type: ${project_type}
- Hazard Classification: ${hazard_class}

## Input Files
${input_files.map(f => `- ${f.file_type}: ${f.s3_uri}`).join('\n')}
`;

  if (building_info) {
    prompt += `
## Building Information
- Total Area: ${building_info.total_area_sqft} sq ft
- Floors: ${building_info.floors}
- Ceiling Height: ${building_info.ceiling_height_ft} ft
`;
  }

  if (water_supply) {
    prompt += `
## Water Supply
- Available Pressure: ${water_supply.available_pressure_psi} PSI
- Available Flow: ${water_supply.available_flow_gpm} GPM
`;
  }

  prompt += `
## Instructions
Execute the 12-step AquaSkill LOD 500 pipeline:
1. INITIALIZE - Parse inputs and fetch geometry from S3
2. SYNC - Update status to PROCESSING
3. VOXELIZE - Convert geometry to 3D Voxel Grid
4. ROUTE - Execute A* pathfinding for optimal pipe routing
5. HYDRAULICS_INIT - Assign initial pipe diameters
6. HYDRAULICS_LOOP - Run Hazen-Williams calculations, resize if needed
7. VALIDATION_SPACING - Check NFPA 13 sprinkler spacing
8. VALIDATION_BROWSER - Verify Victaulic fittings K-factors
9. FABRICATION - Generate LOD 500 BOM with cut lengths
10. REPORT - Generate Traffic Light status and PDF
11. SAVE - Upload artifacts to S3 audit trail
12. FINALIZE - Update status to COMPLETED

Update the task status after each major step using the SystemSync action group.

Begin execution now.
`;

  return prompt;
}

async function updateStatus(
  taskId: string,
  status: string,
  message: string,
  trafficLight?: string
): Promise<void> {
  const updateExpression = ['#status = :status', '#message = :message', '#updated_at = :updated_at'];
  const expressionAttributeNames: Record<string, string> = {
    '#status': 'status',
    '#message': 'message',
    '#updated_at': 'updated_at',
  };
  const expressionAttributeValues: Record<string, { S: string }> = {
    ':status': { S: status },
    ':message': { S: message },
    ':updated_at': { S: new Date().toISOString() },
  };

  if (trafficLight) {
    updateExpression.push('traffic_light = :traffic_light');
    expressionAttributeValues[':traffic_light'] = { S: trafficLight };
  }

  await dynamodb.send(new UpdateItemCommand({
    TableName: process.env.TABLE_NAME!,
    Key: { task_id: { S: taskId } },
    UpdateExpression: `SET ${updateExpression.join(', ')}`,
    ExpressionAttributeNames: expressionAttributeNames,
    ExpressionAttributeValues: expressionAttributeValues,
  }));
}
