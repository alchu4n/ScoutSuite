from ScoutSuite.providers.ksyun.resources.base import KsyunResources
from ScoutSuite.providers.ksyun.facade.base import KsyunFacade


class Instances(KsyunResources):
    def __init__(self, facade: KsyunFacade, region: str):
        super().__init__(facade)
        self.region = region


    async def fetch_all(self):
        project_list = self.facade.kec._credentials.project_list
        if project_list:
            for project_id in project_list:
                raw_instances = await self.facade.kec.get_instances(region=self.region, project_id=project_id)
                if raw_instances:
                    for raw_instance in raw_instances:
                        id, instance = await self._parse_instance(raw_instance)
                        self[id] = instance

    async def _parse_instance(self, raw_instance):

        instance_dict = {}

        instance_dict['id'] = raw_instance.get('InstanceId')
        instance_dict['name'] = raw_instance.get('InstanceName')
        # instance_dict['auto_release_time'] = raw_instance.get('AutoReleaseTime')
        instance_dict['region_id'] = raw_instance.get('AvailabilityZone')
        # instance_dict['dedicated_instance_attribute'] = raw_instance.get('DedicatedUuid')
        # instance_dict['serial_number'] = raw_instance.get('SerialNumber')
        instance_dict['creation_time'] = raw_instance.get('CreationDate')
        # instance_dict['spot_price_limit'] = raw_instance.get('SpotPriceLimit') # DescribePrice
        # instance_dict['expired_time'] = raw_instance.get('ExpiredTime')
        # instance_dict['io_optimized'] = raw_instance.get('IoOptimized')
        instance_dict['memory'] = raw_instance.get('InstanceConfigure').get('MemoryGb')
        instance_dict['os_type'] = raw_instance.get('Platform')
        # instance_dict['internet_charge_type'] = raw_instance.get('ChargeType')
        instance_dict['vpc_attributes'] = raw_instance.get('VncSupport')
        # instance_dict['status'] = raw_instance.get('Status')
        # instance_dict['description'] = raw_instance.get('Description')
        instance_dict['os_name_en'] = raw_instance.get('Platform')
        instance_dict['host_name'] = raw_instance.get('HostName')
        # instance_dict['cluster_id'] = raw_instance.get('ClusterId')
        instance_dict['image_id'] = raw_instance.get('ImageId')
        instance_dict['resource_group_id'] = raw_instance.get('ProjectId')
        # instance_dict['instance_type_family'] = raw_instance.get('InstanceTypeFamily')
        # instance_dict['credit_specification'] = raw_instance.get('CreditSpecification')
        # instance_dict['instance_network_type'] = raw_instance.get('NetworkInterfaceSet').get('NetworkInterfaceType')
        instance_dict['instance_type'] = raw_instance.get('InstanceType')
        # instance_dict['network_interfaces'] = raw_instance.get('NetworkInterfaceSet').get('NetworkInterfaceName')
        instance_dict['eip_address'] = raw_instance.get('EipAddress')
        instance_dict['inner_ip_address'] = raw_instance.get('PrivateIpAddress')
        # instance_dict['gpu_amount'] = raw_instance.get('NetworkInterfaceSet').get('PublicIp')
        instance_dict['operation_locks'] = raw_instance.get('OperationLocks')
        instance_dict['instance_charge_type'] = raw_instance.get('ChargeType')
        # instance_dict['zone_id'] = raw_instance.get('ZoneId')
        # instance_dict['internet_max_bandwidth_out'] = raw_instance.get('InternetMaxBandwidthOut')
        # instance_dict['sale_cycle'] = raw_instance.get('SaleCycle')
        # instance_dict['spot_strategy'] = raw_instance.get('SpotStrategy')
        # instance_dict['security_group_ids'] = raw_instance.get('NetworkInterfaceSet').get('SecurityGroupSet').get('SecurityGroupId')
        # instance_dict['ecs_capacity_reservation_attr'] = raw_instance.get('EcsCapacityReservationAttr')
        instance_dict['cpu'] = raw_instance.get('InstanceConfigure').get('VCPU')
        instance_dict['public_ip_address'] = raw_instance.get('PublicIp')
        # instance_dict['deletion_protection'] = raw_instance.get('DeletionProtection')
        # instance_dict['stopped_mode'] = raw_instance.get('StoppedMode')
        # instance_dict['internet_max_bandwidth_in'] = raw_instance.get('InternetMaxBandwidthIn')
        # instance_dict['deployment_set_id'] = raw_instance.get('DeploymentSetId')
        instance_dict['os_name'] = raw_instance.get('Platform')
        # instance_dict['vlan_id'] = raw_instance.get('VlanId')
        # instance_dict['recyclable'] = raw_instance.get('Recyclable')
        # instance_dict['start_time'] = raw_instance.get('StartTime')
        # instance_dict['gpu_spec'] = raw_instance.get('GPUSpec')
        # instance_dict['device_available'] = raw_instance.get('DeviceAvailable')
        # instance_dict['dedicated_host_attribute'] = raw_instance.get('DedicatedHostAttribute')

        return instance_dict['id'], instance_dict
