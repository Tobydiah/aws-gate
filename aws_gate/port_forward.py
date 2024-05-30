import logging

from aws_gate.constants import AWS_DEFAULT_PROFILE, AWS_DEFAULT_REGION
from aws_gate.decorators import (
    plugin_version,
    plugin_required,
    valid_aws_profile,
    valid_aws_region,
)
from aws_gate.query import query_instance
from aws_gate.session_common import BaseSession
from aws_gate.utils import (
    get_aws_client,
    get_aws_resource,
    fetch_instance_details_from_config,
)

logger = logging.getLogger(__name__)


class SSMPortForwardSession(BaseSession):
    """
    SSM Port Forward Session to Remote via instance.

    Refer to SSM Document: AWS-StartPortForwardingSessionToRemoteHost

    :param instance_id: The instance ID to connect to
    :param target_host: The target host to forward to
    :param region_name: The region name
    :param profile_name: The profile name
    :param target_port: The target port
    :param local_port: The local port
    :param ssm: The SSM client
    """

    def __init__(
        self,
        instance_id,
        target_host: str,
        target_port: int,
        region_name=AWS_DEFAULT_REGION,
        profile_name=AWS_DEFAULT_PROFILE,
        local_port: int = 7000,
        ssm=None,
    ):
        self._instance_id = instance_id
        self._region_name = region_name
        self._profile_name = profile_name if profile_name is not None else ""
        self._ssm = ssm
        self._target_host = target_host
        self._target_port = target_port
        self._local_port = local_port

        start_session_kwargs = dict(
            Target=self._instance_id,
            DocumentName="AWS-StartPortForwardingSessionToRemoteHost",
            Parameters={
                "portNumber": [str(self._target_port)],
                "localPortNumber": [str(self._local_port)],
                "host": [self._target_host],
            },
        )

        self._session_parameters = start_session_kwargs


@plugin_required
@plugin_version("1.1.23.0")
@valid_aws_profile
@valid_aws_region
def port_forward(
    config,
    instance_name,
    target_host,
    target_port,
    local_port=7000,
    profile_name=AWS_DEFAULT_PROFILE,
    region_name=AWS_DEFAULT_REGION,
):
    instance, profile, region = fetch_instance_details_from_config(
        config, instance_name, profile_name, region_name
    )

    ssm = get_aws_client("ssm", region_name=region, profile_name=profile)
    ec2 = get_aws_resource("ec2", region_name=region, profile_name=profile)

    instance_id = query_instance(name=instance, ec2=ec2)
    if instance_id is None:
        raise ValueError(f"No instance could be found for name: {instance}")

    logger.info(
        "Opening SSM Port Forwarding Session to %s:%s via instance %s (%s) via profile %s to %s:%s",
        target_host,
        target_port,
        instance_id,
        region,
        profile,
    )
    with SSMPortForwardSession(
        instance_id,
        region_name=region,
        profile_name=profile,
        ssm=ssm,
        target_host=target_host,
        target_port=target_port,
        local_port=local_port,
    ) as sess:
        sess.open()
