from aws_cdk import (
    Stack,
    CfnOutput,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
)
from constructs import Construct
from aws_cdk.aws_apigatewayv2 import HttpApi, HttpMethod
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from aws_cdk import RemovalPolicy
from aws_cdk import Duration
from aws_cdk.aws_lambda_event_sources import SqsEventSource

class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        tasks_table = dynamodb.Table(
            self,
            "TasksTable",
            partition_key=dynamodb.Attribute(
                name="task_id",
                type=dynamodb.AttributeType.STRING,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        dead_letter_queue = sqs.Queue(
            self,
            "DeadLetterQueue",
            retention_period=Duration.days(7),
        )

        tasks_queue = sqs.Queue(
            self,
            "TasksQueue",
            visibility_timeout=Duration.seconds(180),
            retention_period=Duration.days(1),
            receive_message_wait_time=Duration.seconds(0),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=5,
                queue=dead_letter_queue,
            ),
        )

        api_lambda = _lambda.Function(
            self,
            "AppLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="api_handler.handler",
            code=_lambda.Code.from_asset("../service/src"),
            environment={
                "TASKS_TABLE_NAME": tasks_table.table_name,
                "TASKS_QUEUE_URL": tasks_queue.queue_url,
            },
        )

        worker_lambda = _lambda.Function(
            self,
            "WorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="worker_handler.handler",
            code=_lambda.Code.from_asset("../service/src"),
            timeout=Duration.seconds(30),
            environment={
                "TASKS_TABLE_NAME": tasks_table.table_name,
            },
        )

        worker_lambda.add_event_source(
            SqsEventSource(
                tasks_queue,
                batch_size=1,
                max_batching_window=Duration.seconds(0),
            )
        )

        tasks_table.grant_read_write_data(api_lambda)

        tasks_queue.grant_send_messages(api_lambda)

        api_lambda_integration = HttpLambdaIntegration(
            "AppLambdaIntegration",
            handler=api_lambda,
        )

        tasks_queue.grant_consume_messages(worker_lambda)
        tasks_table.grant_read_write_data(worker_lambda)

        http_api = HttpApi(
            self,
            "AwsAiPlatformServiceApi",
        )

        http_api.add_routes(
            path="/health",
            methods=[HttpMethod.GET],
            integration=api_lambda_integration,
        )

        http_api.add_routes(
            path="/hello",
            methods=[HttpMethod.GET],
            integration=api_lambda_integration,
        )

        http_api.add_routes(
            path="/tasks",
            methods=[HttpMethod.POST],
            integration=api_lambda_integration,
        )

        http_api.add_routes(
            path="/tasks/{id}",
            methods=[HttpMethod.GET],
            integration=api_lambda_integration,
        )

        CfnOutput(
            self,
            "ApiUrl",
            value=http_api.api_endpoint,
        )