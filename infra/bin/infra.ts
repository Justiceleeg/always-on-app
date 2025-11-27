#!/usr/bin/env node
import 'dotenv/config';
import * as cdk from 'aws-cdk-lib/core';
import { JusticeStack } from '../lib/justice-stack';

const app = new cdk.App();
new JusticeStack(app, 'JusticeStack', {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },
});
