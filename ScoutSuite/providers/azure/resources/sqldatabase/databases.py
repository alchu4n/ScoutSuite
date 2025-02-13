from ScoutSuite.providers.azure.facade.base import AzureFacade
from ScoutSuite.providers.azure.resources.base import AzureCompositeResources
from ScoutSuite.providers.azure.utils import get_resource_group_name

from .database_blob_auditing_policies import DatabaseBlobAuditingPolicies
from .database_threat_detection_policies import DatabaseThreatDetectionPolicies
from .replication_links import ReplicationLinks
from .transparent_data_encryptions import TransparentDataEncryptions


class Databases(AzureCompositeResources):
    _children = [
        (DatabaseBlobAuditingPolicies, 'auditing'),
        (DatabaseThreatDetectionPolicies, 'threat_detection'),
        (ReplicationLinks, None),
        (TransparentDataEncryptions, None)
    ]

    def __init__(self, facade: AzureFacade, resource_group_name: str, server_name: str, subscription_id: str):
        super().__init__(facade)
        self.resource_group_name = resource_group_name
        self.server_name = server_name
        self.subscription_id = subscription_id

    async def fetch_all(self):
        for db in await self.facade.sqldatabase.get_databases(
                self.resource_group_name, self.server_name, self.subscription_id):
            # We do not want to scan 'master' database which is auto-generated by Azure and read-only:
            if db.name == 'master':
                continue

            self[db.name] = {
                'id': db.name,
                'name': db.name,
                'tags': ["{}:{}".format(key, value) for key, value in db.tags.items()] if db.tags is not None else [],
                'resource_group_name': get_resource_group_name(db.id)
            }

        await self._fetch_children_of_all_resources(
            resources=self,
            scopes={db_id: {'resource_group_name': self.resource_group_name,
                            'server_name': self.server_name,
                            'database_name': db['name'],
                            'subscription_id': self.subscription_id}
                    for (db_id, db) in self.items()}
        )
