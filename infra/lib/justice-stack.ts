import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';

const PREFIX = 'jpwhite';

export class JusticeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const audioBucket = new s3.Bucket(this, 'AudioStorageBucket', {
      bucketName: `${PREFIX}-audio-storage-${this.account}`,
      versioned: true,
      publicReadAccess: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
      cors: [
        {
          allowedOrigins: ['*'],
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedHeaders: ['*'],
          exposedHeaders: ['ETag'],
          maxAge: 3000,
        },
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    new cdk.CfnOutput(this, 'AudioBucketName', {
      value: audioBucket.bucketName,
      exportName: 'AudioBucketName',
    });

    // Stage 2: Aurora Postgres
    // Use default VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', {
      isDefault: true,
    });

    // Security group for Aurora (will allow ECS access in Stage 3)
    const auroraSecurityGroup = new ec2.SecurityGroup(this, 'AuroraSecurityGroup', {
      vpc,
      description: 'Security group for Aurora Postgres',
      allowAllOutbound: true,
    });

    // Security group for ECS (created here so Aurora can reference it)
    const ecsSecurityGroup = new ec2.SecurityGroup(this, 'ECSSecurityGroup', {
      vpc,
      description: 'Security group for ECS tasks',
      allowAllOutbound: true,
    });

    // Allow ECS to connect to Aurora on port 5432
    auroraSecurityGroup.addIngressRule(
      ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from ECS'
    );

    // Allow PostgreSQL access from all IPs (for external connections)
    auroraSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from all IPs'
    );

    // Load DB credentials from .env
    const dbUsername = process.env.DB_USERNAME as string;
    const dbPassword = process.env.DB_PASSWORD as string;

    if (!dbPassword) {
      throw new Error("DB_PASSWORD must be set in your .env file");
    }

    // Load Firebase credentials from environment variables
    // const firebaseProjectId = process.env.FIREBASE_PROJECT_ID || '';
    // const firebasePrivateKey = process.env.FIREBASE_PRIVATE_KEY || '';
    // const firebaseClientEmail = process.env.FIREBASE_CLIENT_EMAIL || '';

    // Create Aurora Serverless v2 cluster
    const auroraCluster = new rds.DatabaseCluster(this, 'AuroraCluster', {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_17_5,
      }),
      credentials: rds.Credentials.fromUsername(dbUsername, {
        password: cdk.SecretValue.unsafePlainText(dbPassword),
      }),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 1,
      defaultDatabaseName: 'frontier_audio',
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      securityGroups: [auroraSecurityGroup],
      writer: rds.ClusterInstance.serverlessV2('writer'),
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Export values for use in other stages
    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      exportName: `${PREFIX}-VpcId`,
    });

    new cdk.CfnOutput(this, 'ECSSecurityGroupId', {
      value: ecsSecurityGroup.securityGroupId,
      exportName: `${PREFIX}-ECSSecurityGroupId`,
    });

    new cdk.CfnOutput(this, 'AuroraClusterEndpoint', {
      value: auroraCluster.clusterEndpoint.hostname,
      exportName: `${PREFIX}-AuroraClusterEndpoint`,
    });
  }
}
