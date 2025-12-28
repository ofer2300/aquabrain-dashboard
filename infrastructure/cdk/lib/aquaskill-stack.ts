import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as nodejs from 'aws-cdk-lib/aws-lambda-nodejs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';
import * as path from 'path';
import * as fs from 'fs';

export interface AquaSkillStackProps extends cdk.StackProps {
  environment: 'dev' | 'staging' | 'prod';
}

export class AquaSkillStack extends cdk.Stack {
  public readonly inputBucket: s3.Bucket;
  public readonly auditBucket: s3.Bucket;
  public readonly table: dynamodb.Table;
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: AquaSkillStackProps) {
    super(scope, id, props);

    const envPrefix = props.environment;

    // ==========================================================================
    // 1. STORAGE & STATE
    // ==========================================================================

    // Input bucket for RVT/DXF/DWG files
    this.inputBucket = new s3.Bucket(this, 'InputBucket', {
      bucketName: `aquabrain-projects-input-${envPrefix}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      cors: [{
        allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
        allowedOrigins: ['*'],
        allowedHeaders: ['*'],
      }],
      lifecycleRules: [{
        expiration: cdk.Duration.days(90),
        transitions: [{
          storageClass: s3.StorageClass.GLACIER,
          transitionAfter: cdk.Duration.days(30),
        }],
      }],
    });

    // Audit trail bucket for PDFs and logs
    this.auditBucket = new s3.Bucket(this, 'AuditBucket', {
      bucketName: `aquabrain-audit-trail-${envPrefix}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: true,
      lifecycleRules: [{
        expiration: cdk.Duration.days(365 * 7), // 7 years for compliance
      }],
    });

    // Results bucket for LOD 500 outputs
    const resultsBucket = new s3.Bucket(this, 'ResultsBucket', {
      bucketName: `aquabrain-lod500-results-${envPrefix}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // DynamoDB table for skill execution tracking
    this.table = new dynamodb.Table(this, 'SkillExecutionTable', {
      tableName: `SkillExecution-${envPrefix}`,
      partitionKey: { name: 'task_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
      timeToLiveAttribute: 'ttl',
    });

    // GSI for project-based queries
    this.table.addGlobalSecondaryIndex({
      indexName: 'ProjectIndex',
      partitionKey: { name: 'project_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI for status-based queries
    this.table.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // ==========================================================================
    // 2. BEDROCK AGENT IDENTITY & PERMISSIONS
    // ==========================================================================

    const agentRole = new iam.Role(this, 'AgentRole', {
      roleName: `AquaSkill-Agent-Role-${envPrefix}`,
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: 'Execution role for AquaSkill Bedrock Agent',
    });

    // S3 access for Agent
    agentRole.addToPolicy(new iam.PolicyStatement({
      sid: 'S3DataPlane',
      actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
      resources: [
        this.inputBucket.bucketArn,
        `${this.inputBucket.bucketArn}/*`,
        this.auditBucket.bucketArn,
        `${this.auditBucket.bucketArn}/*`,
        resultsBucket.bucketArn,
        `${resultsBucket.bucketArn}/*`,
      ],
    }));

    // Foundation Model access (Claude 3.5 Sonnet)
    agentRole.addToPolicy(new iam.PolicyStatement({
      sid: 'FoundationModelAccess',
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: [
        'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0',
        'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
      ],
    }));

    // Code Interpreter access
    agentRole.addToPolicy(new iam.PolicyStatement({
      sid: 'CodeInterpreterAccess',
      actions: [
        'bedrock:InvokeModelWithResponseStream',
        'bedrock:Retrieve',
      ],
      resources: ['*'],
    }));

    // ==========================================================================
    // 3. LAMBDA FUNCTIONS
    // ==========================================================================

    // Common Lambda environment
    const lambdaEnvironment = {
      TABLE_NAME: this.table.tableName,
      INPUT_BUCKET: this.inputBucket.bucketName,
      AUDIT_BUCKET: this.auditBucket.bucketName,
      RESULTS_BUCKET: resultsBucket.bucketName,
      ENVIRONMENT: envPrefix,
    };

    // Update Status Lambda (called by Bedrock Agent Action Group)
    const updateStatusLambda = new nodejs.NodejsFunction(this, 'UpdateStatusLambda', {
      functionName: `AquaSkill-UpdateStatus-${envPrefix}`,
      runtime: lambda.Runtime.NODEJS_20_X,
      entry: path.join(__dirname, '../lambda/update-status/index.ts'),
      handler: 'handler',
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: lambdaEnvironment,
    });
    this.table.grantWriteData(updateStatusLambda);

    // Trigger Lambda (API Gateway -> SQS)
    const triggerLambda = new nodejs.NodejsFunction(this, 'TriggerLambda', {
      functionName: `AquaSkill-Trigger-${envPrefix}`,
      runtime: lambda.Runtime.NODEJS_20_X,
      entry: path.join(__dirname, '../lambda/trigger/index.ts'),
      handler: 'handler',
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: lambdaEnvironment,
    });
    this.table.grantWriteData(triggerLambda);

    // Status Lambda (for polling)
    const statusLambda = new nodejs.NodejsFunction(this, 'StatusLambda', {
      functionName: `AquaSkill-Status-${envPrefix}`,
      runtime: lambda.Runtime.NODEJS_20_X,
      entry: path.join(__dirname, '../lambda/status/index.ts'),
      handler: 'handler',
      timeout: cdk.Duration.seconds(10),
      memorySize: 256,
      environment: lambdaEnvironment,
    });
    this.table.grantReadData(statusLambda);

    // ==========================================================================
    // 4. SQS QUEUE FOR JOB PROCESSING
    // ==========================================================================

    const dlq = new sqs.Queue(this, 'DeadLetterQueue', {
      queueName: `AquaSkill-DLQ-${envPrefix}`,
      retentionPeriod: cdk.Duration.days(14),
    });

    const jobQueue = new sqs.Queue(this, 'JobQueue', {
      queueName: `AquaSkill-Jobs-${envPrefix}.fifo`,
      fifo: true,
      contentBasedDeduplication: true,
      visibilityTimeout: cdk.Duration.minutes(35), // > 30 min Agent runtime
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 3,
      },
    });

    triggerLambda.addEnvironment('QUEUE_URL', jobQueue.queueUrl);
    jobQueue.grantSendMessages(triggerLambda);

    // ==========================================================================
    // 5. WORKER LAMBDA (INVOKES BEDROCK AGENT)
    // ==========================================================================

    const workerLambda = new nodejs.NodejsFunction(this, 'WorkerLambda', {
      functionName: `AquaSkill-Worker-${envPrefix}`,
      runtime: lambda.Runtime.NODEJS_20_X,
      entry: path.join(__dirname, '../lambda/worker/index.ts'),
      handler: 'handler',
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        ...lambdaEnvironment,
        AGENT_ID: '', // Will be set after Agent creation
        AGENT_ALIAS_ID: 'TSTALIASID', // Use proper alias in prod
      },
    });

    jobQueue.grantConsumeMessages(workerLambda);
    this.table.grantWriteData(workerLambda);

    // Add Bedrock Agent invocation permission
    workerLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeAgent'],
      resources: ['*'], // Will be scoped after Agent creation
    }));

    // SQS Event Source
    workerLambda.addEventSource(new lambdaEventSources.SqsEventSource(jobQueue, {
      batchSize: 1,
      maxBatchingWindow: cdk.Duration.seconds(0),
    }));

    // ==========================================================================
    // 6. BEDROCK AGENT DEFINITION (L1 Construct)
    // ==========================================================================

    // Load agent instructions
    const agentInstructions = fs.readFileSync(
      path.join(__dirname, '../config/agent_instructions.json'),
      'utf-8'
    );
    const instructions = JSON.parse(agentInstructions);

    // OpenAPI Schema for Action Group
    const actionGroupSchema = {
      openapi: '3.0.1',
      info: {
        title: 'AquaSkill System Sync API',
        version: '1.0.0',
      },
      paths: {
        '/update-status': {
          post: {
            operationId: 'updateStatus',
            description: 'Updates task status in DynamoDB',
            parameters: [
              { name: 'task_id', in: 'query', required: true, schema: { type: 'string' } },
              { name: 'status', in: 'query', required: true, schema: { type: 'string', enum: ['QUEUED', 'PROCESSING', 'VALIDATING', 'COMPLETED', 'FAILED'] } },
              { name: 'traffic_light', in: 'query', schema: { type: 'string', enum: ['GREEN', 'YELLOW', 'RED'] } },
              { name: 'current_step', in: 'query', schema: { type: 'integer' } },
              { name: 'total_steps', in: 'query', schema: { type: 'integer' } },
              { name: 'pdf_url', in: 'query', schema: { type: 'string' } },
              { name: 'message', in: 'query', schema: { type: 'string' } },
            ],
            responses: {
              '200': { description: 'Status updated successfully' },
            },
          },
        },
        '/save-artifact': {
          post: {
            operationId: 'saveArtifact',
            description: 'Saves an artifact to S3 audit trail',
            requestBody: {
              required: true,
              content: {
                'application/json': {
                  schema: {
                    type: 'object',
                    properties: {
                      task_id: { type: 'string' },
                      artifact_type: { type: 'string', enum: ['pdf', 'json', 'csv', 'dxf'] },
                      content: { type: 'string' },
                      filename: { type: 'string' },
                    },
                  },
                },
              },
            },
            responses: {
              '200': { description: 'Artifact saved successfully' },
            },
          },
        },
      },
    };

    const agent = new bedrock.CfnAgent(this, 'AquaSkillAgent', {
      agentName: `AquaSkill-LOD500-${envPrefix}`,
      agentResourceRoleArn: agentRole.roleArn,
      foundationModel: 'anthropic.claude-3-5-sonnet-20240620-v1:0',
      idleSessionTtlInSeconds: 1800, // 30 minutes
      instruction: `
        ${instructions.role}

        OBJECTIVE: ${instructions.objective}

        FRAMEWORK: ${instructions.framework}

        CRITICAL CONSTRAINTS:
        ${instructions.critical_constraints.map((c: string, i: number) => `${i + 1}. ${c}`).join('\n')}

        EXECUTION PLAN:
        ${instructions.plan_template.join('\n')}

        ADDITIONAL GUIDELINES:
        - Always respond in Hebrew when the user writes in Hebrew
        - Use Israeli Standard ת"י 1596 for water tank sizing
        - Generate Traffic Light status (GREEN/YELLOW/RED) for all validations
        - Create audit trail with timestamps for all operations
        - Cite NFPA 13 section numbers for any requirement you mention
      `,
      actionGroups: [{
        actionGroupName: 'SystemSync',
        actionGroupExecutor: {
          lambda: updateStatusLambda.functionArn,
        },
        apiSchema: {
          payload: JSON.stringify(actionGroupSchema),
        },
        description: 'Update system status and save artifacts',
      }],
    });

    // Grant Bedrock permission to invoke Lambda
    updateStatusLambda.addPermission('BedrockInvoke', {
      principal: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      sourceArn: agent.attrAgentArn,
    });

    // Update Worker Lambda with Agent ID
    workerLambda.addEnvironment('AGENT_ID', agent.attrAgentId);

    // Agent Alias for production
    const agentAlias = new bedrock.CfnAgentAlias(this, 'AgentAlias', {
      agentId: agent.attrAgentId,
      agentAliasName: envPrefix,
      description: `${envPrefix} alias for AquaSkill Agent`,
    });

    workerLambda.addEnvironment('AGENT_ALIAS_ID', agentAlias.attrAgentAliasId);

    // ==========================================================================
    // 7. API GATEWAY
    // ==========================================================================

    this.api = new apigateway.RestApi(this, 'AquaSkillApi', {
      restApiName: `AquaSkill-API-${envPrefix}`,
      description: 'AquaSkill LOD 500 Automation API',
      deployOptions: {
        stageName: envPrefix,
        throttlingRateLimit: 100,
        throttlingBurstLimit: 200,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization', 'X-Api-Key'],
      },
    });

    // POST /trigger-aquaskill
    const triggerResource = this.api.root.addResource('trigger-aquaskill');
    triggerResource.addMethod('POST', new apigateway.LambdaIntegration(triggerLambda), {
      apiKeyRequired: false, // Set to true in prod
    });

    // GET /status/{task_id}
    const statusResource = this.api.root.addResource('status');
    const taskIdResource = statusResource.addResource('{task_id}');
    taskIdResource.addMethod('GET', new apigateway.LambdaIntegration(statusLambda));

    // ==========================================================================
    // 8. OUTPUTS
    // ==========================================================================

    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
      description: 'AquaSkill API Gateway Endpoint',
    });

    new cdk.CfnOutput(this, 'AgentId', {
      value: agent.attrAgentId,
      description: 'Bedrock Agent ID',
    });

    new cdk.CfnOutput(this, 'AgentAliasId', {
      value: agentAlias.attrAgentAliasId,
      description: 'Bedrock Agent Alias ID',
    });

    new cdk.CfnOutput(this, 'InputBucketName', {
      value: this.inputBucket.bucketName,
      description: 'S3 Input Bucket',
    });

    new cdk.CfnOutput(this, 'TableName', {
      value: this.table.tableName,
      description: 'DynamoDB Table Name',
    });
  }
}
