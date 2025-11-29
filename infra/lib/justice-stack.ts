import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';

const PREFIX = 'jpwhite';
const DOMAIN_NAME = 'gauntlet3.com';
const SUBDOMAIN = 'jpwhite';
const FULL_DOMAIN = `${SUBDOMAIN}.${DOMAIN_NAME}`;

export class JusticeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Use default VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', {
      isDefault: true,
    });

    // ==================== Route 53 & ACM Certificate ====================

    // Look up existing hosted zone
    const hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
      domainName: DOMAIN_NAME,
    });

    // Create ACM certificate with DNS validation
    const certificate = new acm.Certificate(this, 'Certificate', {
      domainName: FULL_DOMAIN,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // ==================== Security Groups ====================

    // Security group for Aurora
    const auroraSecurityGroup = new ec2.SecurityGroup(this, 'AuroraSecurityGroup', {
      vpc,
      description: 'Security group for Aurora Postgres',
      allowAllOutbound: true,
    });

    // Security group for ECS tasks
    const ecsSecurityGroup = new ec2.SecurityGroup(this, 'ECSSecurityGroup', {
      vpc,
      description: 'Security group for ECS tasks',
      allowAllOutbound: true,
    });

    // Security group for ALB
    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc,
      description: 'Security group for Application Load Balancer',
      allowAllOutbound: true,
    });

    // Allow ALB to receive HTTP traffic from anywhere
    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP traffic'
    );

    // Allow ALB to receive HTTPS traffic from anywhere (for future use)
    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic'
    );

    // Allow ECS to receive traffic from ALB
    ecsSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8000),
      'Allow traffic from ALB'
    );

    // Allow ECS to connect to Aurora on port 5432
    auroraSecurityGroup.addIngressRule(
      ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from ECS'
    );

    // Allow PostgreSQL access from all IPs (for external connections during dev)
    auroraSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from all IPs'
    );

    // ==================== Aurora PostgreSQL ====================

    // Load DB credentials from .env
    const dbUsername = process.env.DB_USERNAME as string;
    const dbPassword = process.env.DB_PASSWORD as string;

    if (!dbPassword) {
      throw new Error("DB_PASSWORD must be set in your .env file");
    }

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

    // ==================== ECR Repository ====================

    const ecrRepository = new ecr.Repository(this, 'BackendRepository', {
      repositoryName: `${PREFIX}-frontier-backend`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: true,
      imageScanOnPush: true,
    });

    // ==================== ECS Cluster ====================

    const ecsCluster = new ecs.Cluster(this, 'FrontierCluster', {
      vpc,
      clusterName: `${PREFIX}-frontier-cluster`,
      containerInsights: true,
    });

    // ==================== CloudWatch Log Group ====================

    const logGroup = new logs.LogGroup(this, 'BackendLogGroup', {
      logGroupName: `/ecs/${PREFIX}-frontier-backend`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ==================== IAM Roles ====================

    // Task Execution Role - allows ECS to pull images and write logs
    const taskExecutionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Task Role - permissions for the running container (minimal for MVP)
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // ==================== ECS Task Definition ====================

    // Load environment variables for ECS task
    const firebaseProjectId = process.env.FIREBASE_PROJECT_ID || '';
    const firebasePrivateKey = process.env.FIREBASE_PRIVATE_KEY || '';
    const firebaseClientEmail = process.env.FIREBASE_CLIENT_EMAIL || '';
    const openaiApiKey = process.env.OPENAI_API_KEY || '';

    const taskDefinition = new ecs.FargateTaskDefinition(this, 'BackendTaskDef', {
      memoryLimitMiB: 1024,
      cpu: 512, // 0.5 vCPU
      executionRole: taskExecutionRole,
      taskRole: taskRole,
      family: `${PREFIX}-frontier-backend`,
    });

    // Construct DATABASE_URL from Aurora endpoint
    const databaseUrl = `postgresql+asyncpg://${dbUsername}:${dbPassword}@${auroraCluster.clusterEndpoint.hostname}:5432/frontier_audio`;

    const container = taskDefinition.addContainer('BackendContainer', {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, 'latest'),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'backend',
        logGroup: logGroup,
      }),
      environment: {
        DATABASE_URL: databaseUrl,
        FIREBASE_PROJECT_ID: firebaseProjectId,
        FIREBASE_PRIVATE_KEY: firebasePrivateKey,
        FIREBASE_CLIENT_EMAIL: firebaseClientEmail,
        OPENAI_API_KEY: openaiApiKey,
        SPEAKER_VERIFICATION_THRESHOLD: '0.65',
      },
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
    });

    container.addPortMappings({
      containerPort: 8000,
      protocol: ecs.Protocol.TCP,
    });

    // ==================== Application Load Balancer ====================

    const alb = new elbv2.ApplicationLoadBalancer(this, 'FrontierALB', {
      vpc,
      internetFacing: true,
      loadBalancerName: `${PREFIX}-frontier-alb`,
      securityGroup: albSecurityGroup,
    });

    // HTTPS Listener with ACM certificate
    const httpsListener = alb.addListener('HTTPSListener', {
      port: 443,
      protocol: elbv2.ApplicationProtocol.HTTPS,
      certificates: [certificate],
    });

    // HTTP Listener - redirect to HTTPS
    alb.addListener('HTTPListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultAction: elbv2.ListenerAction.redirect({
        protocol: 'HTTPS',
        port: '443',
        permanent: true,
      }),
    });

    // ==================== ECS Service ====================

    const ecsService = new ecs.FargateService(this, 'BackendService', {
      cluster: ecsCluster,
      taskDefinition: taskDefinition,
      desiredCount: 1,
      securityGroups: [ecsSecurityGroup],
      assignPublicIp: true, // Required for public subnets to pull images
      serviceName: `${PREFIX}-frontier-backend`,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
    });

    // Register ECS service as target for ALB
    httpsListener.addTargets('BackendTarget', {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [ecsService],
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
    });

    // ==================== Route 53 DNS Record ====================

    // Create A record pointing subdomain to ALB
    new route53.ARecord(this, 'ALBRecord', {
      zone: hostedZone,
      recordName: SUBDOMAIN,
      target: route53.RecordTarget.fromAlias(new route53Targets.LoadBalancerTarget(alb)),
    });

    // ==================== CloudFormation Outputs ====================

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

    new cdk.CfnOutput(this, 'ECRRepositoryUri', {
      value: ecrRepository.repositoryUri,
      exportName: `${PREFIX}-ECRRepositoryUri`,
    });

    new cdk.CfnOutput(this, 'ECSClusterName', {
      value: ecsCluster.clusterName,
      exportName: `${PREFIX}-ECSClusterName`,
    });

    new cdk.CfnOutput(this, 'ECSServiceName', {
      value: ecsService.serviceName,
      exportName: `${PREFIX}-ECSServiceName`,
    });

    new cdk.CfnOutput(this, 'ALBDnsName', {
      value: alb.loadBalancerDnsName,
      exportName: `${PREFIX}-ALBDnsName`,
      description: 'DNS name of the Application Load Balancer',
    });

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: `https://${FULL_DOMAIN}`,
      exportName: `${PREFIX}-ApiUrl`,
      description: 'HTTPS URL of the API',
    });
  }
}
