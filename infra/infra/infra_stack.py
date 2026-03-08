from typing import cast

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_lambda as _lambda,
)
from constructs import Construct
from aws_cdk.aws_apigatewayv2 import HttpApi, HttpMethod
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        health_lambda = _lambda.Function(
            self,
            "HealthLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../service/src"),
        )

        http_api = HttpApi(
            self,
            "AwsAiPlatformServiceApi",
        )

        health_integration = HttpLambdaIntegration(
            "HealthIntegration",
            handler=health_lambda,
        )

        http_api.add_routes(
            path="/health",
            methods=[HttpMethod.GET],
            integration=health_integration,
        )

        CfnOutput(
            self,
            "ApiUrl",
            value=http_api.api_endpoint,
        )