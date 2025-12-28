#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AquaSkillStack } from '../lib/aquaskill-stack';

const app = new cdk.App();

// Development environment
new AquaSkillStack(app, 'AquaSkill-dev', {
  environment: 'dev',
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
  description: 'AquaSkill LOD 500 Fire Sprinkler Design Automation - Development',
  tags: {
    Project: 'AquaBrain',
    Component: 'AquaSkill',
    Environment: 'dev',
    ManagedBy: 'CDK',
  },
});

// Staging environment
new AquaSkillStack(app, 'AquaSkill-staging', {
  environment: 'staging',
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
  description: 'AquaSkill LOD 500 Fire Sprinkler Design Automation - Staging',
  tags: {
    Project: 'AquaBrain',
    Component: 'AquaSkill',
    Environment: 'staging',
    ManagedBy: 'CDK',
  },
});

// Production environment
new AquaSkillStack(app, 'AquaSkill-prod', {
  environment: 'prod',
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
  description: 'AquaSkill LOD 500 Fire Sprinkler Design Automation - Production',
  tags: {
    Project: 'AquaBrain',
    Component: 'AquaSkill',
    Environment: 'prod',
    ManagedBy: 'CDK',
  },
});

app.synth();
