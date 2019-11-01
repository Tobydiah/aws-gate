import json
import logging

from aws_gate.constants import (
    AWS_DEFAULT_PROFILE,
    AWS_DEFAULT_REGION,
    DEFAULT_OS_USER,
    DEFAULT_SSH_PORT,
    DEFAULT_KEY_ALGORITHM,
    DEFAULT_KEY_SIZE,
    DEFAULT_GATE_KEY_PATH,
    PLUGIN_INSTALL_PATH,
)
from aws_gate.decorators import (
    plugin_version,
    plugin_required,
    valid_aws_profile,
    valid_aws_region,
)
from aws_gate.query import query_instance
from aws_gate.session_common import BaseSession
from aws_gate.ssh_common import SshKey, SshKeyUploader
from aws_gate.utils import (
    get_aws_client,
    get_aws_resource,
    fetch_instance_details_from_config,
    get_instance_details,
    execute,
)

logger = logging.getLogger(__name__)


class SshSession(BaseSession):
    def __init__(
        self,
        instance_id,
        ssm=None,
        region_name=AWS_DEFAULT_REGION,
        profile_name=AWS_DEFAULT_PROFILE,
        port=DEFAULT_SSH_PORT,
        user=DEFAULT_OS_USER,
    ):
        self._instance_id = instance_id
        self._region_name = region_name
        self._profile_name = profile_name if profile_name is not None else ""
        self._ssm = ssm
        self._port = port
        self._user = user

        self._session_parameters = {
            "Target": self._instance_id,
            "DocumentName": "AWS-StartSSHSession",
            "Parameters": {"portNumber": [str(self._port)]},
        }

    def _build_ssh_command(self):

        plugin_args = [
            json.dumps(self._response),
            self._region_name,
            "StartSession",
            self._profile_name,
            json.dumps(self._session_parameters),
            "https://ssm.amazonaws.com",  # self._ssm.meta.endpoint_url,
        ]

        cmd = ["ssh"]
        cmd.append("-F")
        cmd.append("/dev/null")
        cmd.append("-p")
        cmd.append(str(self._port))
        cmd.append("-l")
        cmd.append(self._user)
        cmd.append("-i")
        cmd.append(DEFAULT_GATE_KEY_PATH)
        cmd.append("-o")
        cmd.append("IdentitiesOnly=yes")
        cmd.append("-o")
        cmd.append("Proxycommand={} {}".format(PLUGIN_INSTALL_PATH, plugin_args))
        cmd.append(self._instance_id)

        return cmd

    def open(self):
        ssh_cmd = self._build_ssh_command()

        return execute(ssh_cmd[0], ssh_cmd[1:])


@plugin_required
@plugin_version("1.1.23.0")
@valid_aws_profile
@valid_aws_region
def ssh(
    config,
    instance_name,
    user=DEFAULT_OS_USER,
    port=DEFAULT_SSH_PORT,
    key_type=DEFAULT_KEY_ALGORITHM,
    key_size=DEFAULT_KEY_SIZE,
    profile_name=AWS_DEFAULT_PROFILE,
    region_name=AWS_DEFAULT_REGION,
):
    instance, profile, region = fetch_instance_details_from_config(
        config, instance_name, profile_name, region_name
    )

    ssm = get_aws_client("ssm", region_name=region, profile_name=profile)
    ec2 = get_aws_resource("ec2", region_name=region, profile_name=profile)
    ec2_ic = get_aws_client(
        "ec2-instance-connect", region_name=region, profile_name=profile
    )

    instance_id = query_instance(name=instance, ec2=ec2)
    if instance_id is None:
        raise ValueError("No instance could be found for name: {}".format(instance))

    az = get_instance_details(instance_id=instance_id, ec2=ec2)["availability_zone"]

    logger.info(
        "Opening SSH session on instance %s (%s) via profile %s",
        instance_id,
        region,
        profile,
    )
    with SshKey(key_type=key_type, key_size=key_size) as ssh_key:
        with SshKeyUploader(
            instance_id=instance_id, az=az, user=user, ssh_key=ssh_key, ec2_ic=ec2_ic
        ):
            with SshSession(
                instance_id,
                region_name=region,
                profile_name=profile,
                ssm=ssm,
                port=port,
                user=user,
            ) as ssh_proxy_session:
                ssh_proxy_session.open()
