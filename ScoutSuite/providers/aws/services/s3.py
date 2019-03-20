# -*- coding: utf-8 -*-
"""
S3-related classes and functions
"""

import json

from botocore.exceptions import ClientError

from ScoutSuite.core.console import print_error, print_exception, print_info
from ScoutSuite.providers.aws.utils import handle_truncated_response
from ScoutSuite.providers.aws.configs.base import AWSBaseConfig
from ScoutSuite.utils import manage_dictionary


########################################
# S3Config
########################################


class S3Config(AWSBaseConfig):
    """
    S3 configuration for all AWS regions

    :cvar targets:                      Tuple with all S3 resource names that may be fetched
    """
    targets = (
        ('buckets', 'Buckets', 'list_buckets', {}, False),
    )

    def __init__(self, thread_config):
        self.buckets = {}
        self.buckets_count = 0
        super(S3Config, self).__init__(thread_config)

    def parse_buckets(self, bucket, params):
        """
        Parse a single S3 bucket

        TODO:
        - CORS
        - Lifecycle
        - Notification ?
        - Get bucket's policy

        :param bucket:
        :param params:
        :return:
        """
        bucket['name'] = bucket.pop('Name')
        api_client = params['api_clients'][get_s3_list_region(list(params['api_clients'].keys())[0])]

        bucket['CreationDate'] = str(bucket['CreationDate'])
        bucket['region'] = get_s3_bucket_location(api_client, bucket['name'])
        # h4ck :: fix issue #59, location constraint can be EU or eu-west-1 for Ireland...
        if bucket['region'] == 'EU':
            bucket['region'] = 'eu-west-1'
        # h4ck :: S3 is global but region-aware...
        if bucket['region'] not in params['api_clients']:
            print_info('Skipping bucket %s (region %s outside of scope)' % (bucket['name'], bucket['region']))
            self.buckets_count -= 1
            return

        api_client = params['api_clients'][bucket['region']]
        get_s3_bucket_logging(api_client, bucket['name'], bucket)
        get_s3_bucket_versioning(api_client, bucket['name'], bucket)
        get_s3_bucket_webhosting(api_client, bucket['name'], bucket)
        get_s3_bucket_default_encryption(api_client, bucket['name'], bucket)
        bucket['grantees'] = get_s3_acls(api_client, bucket['name'], bucket)
        get_s3_bucket_policy(api_client, bucket['name'], bucket)
        get_s3_bucket_secure_transport(api_client, bucket['name'], bucket)
        # If requested, get key properties
        bucket['id'] = self.get_non_provider_id(bucket['name'])
        self.buckets[bucket['id']] = bucket

def init_s3_permissions():
    permissions = {'read': False, 'write': False, 'read_acp': False, 'write_acp': False}
    return permissions


def set_s3_permissions(permissions, name):
    if name == 'READ' or name == 'FULL_CONTROL':
        permissions['read'] = True
    if name == 'WRITE' or name == 'FULL_CONTROL':
        permissions['write'] = True
    if name == 'READ_ACP' or name == 'FULL_CONTROL':
        permissions['read_acp'] = True
    if name == 'WRITE_ACP' or name == 'FULL_CONTROL':
        permissions['write_acp'] = True




def get_s3_acls(api_client, bucket_name, bucket, key_name=None):
    try:
        grantees = {}
        if key_name:
            grants = api_client.get_object_acl(Bucket=bucket_name, Key=key_name)
        else:
            grants = api_client.get_bucket_acl(Bucket=bucket_name)
        for grant in grants['Grants']:
            if 'ID' in grant['Grantee']:
                grantee = grant['Grantee']['ID']
                display_name = grant['Grantee']['DisplayName'] if \
                    'DisplayName' in grant['Grantee'] else grant['Grantee']['ID']
            elif 'URI' in grant['Grantee']:
                grantee = grant['Grantee']['URI'].split('/')[-1]
                display_name = s3_group_to_string(grant['Grantee']['URI'])
            else:
                grantee = display_name = 'Unknown'
            permission = grant['Permission']
            manage_dictionary(grantees, grantee, {})
            grantees[grantee]['DisplayName'] = display_name
            if 'URI' in grant['Grantee']:
                grantees[grantee]['URI'] = grant['Grantee']['URI']
            manage_dictionary(grantees[grantee], 'permissions', init_s3_permissions())
            set_s3_permissions(grantees[grantee]['permissions'], permission)
        return grantees
    except Exception as e:
        print_error('Failed to get ACL configuration for %s: %s' % (bucket_name, e))
        return {}


def get_s3_bucket_policy(api_client, bucket_name, bucket_info):
    try:
        bucket_info['policy'] = json.loads(api_client.get_bucket_policy(Bucket=bucket_name)['Policy'])
        return True
    except Exception as e:
        if not (type(e) == ClientError and e.response['Error']['Code'] == 'NoSuchBucketPolicy'):
            print_error('Failed to get bucket policy for %s: %s' % (bucket_name, e))
        return False


def get_s3_bucket_secure_transport(api_client, bucket_name, bucket_info):
    try:
        if 'policy' in bucket_info:
            bucket_info['secure_transport_enabled'] = False
            for statement in bucket_info['policy']['Statement']:
                # evaluate statement to see if it contains a condition disallowing HTTP transport
                # TODO this might not cover all cases
                if 'Condition' in statement and \
                        'Bool' in statement['Condition'] and \
                        'aws:SecureTransport' in statement['Condition']['Bool'] and \
                        ((statement['Condition']['Bool']['aws:SecureTransport'] == 'false' and
                          statement['Effect'] == 'Deny') or
                         (statement['Condition']['Bool']['aws:SecureTransport'] == 'true' and
                          statement['Effect'] == 'Allow')):
                    bucket_info['secure_transport_enabled'] = True
            return True
        else:
            bucket_info['secure_transport_enabled'] = False
            return True
    except Exception as e:
        print_error('Failed to get evaluate bucket policy for %s: %s' % (bucket_name, e))
        bucket_info['secure_transport'] = None
        return False


# noinspection PyBroadException
def get_s3_bucket_versioning(api_client, bucket_name, bucket_info):
    try:
        versioning = api_client.get_bucket_versioning(Bucket=bucket_name)
        bucket_info['versioning_status_enabled'] = _status_to_bool(versioning.get('Status'))
        bucket_info['version_mfa_delete_enabled'] = _status_to_bool(versioning.get('MFADelete'))
        return True
    except Exception:
        bucket_info['versioning_status_enabled'] = None
        bucket_info['version_mfa_delete_enabled'] = None
        return False


def _status_to_bool(value):
    """ Converts a string to True if it is equal to 'Enabled' or to False otherwise. """
    return value == 'Enabled'


def get_s3_bucket_logging(api_client, bucket_name, bucket_info):
    try:
        logging = api_client.get_bucket_logging(Bucket=bucket_name)
        if 'LoggingEnabled' in logging:
            bucket_info['logging'] = \
                logging['LoggingEnabled']['TargetBucket'] + '/' + logging['LoggingEnabled']['TargetPrefix']
            bucket_info['logging_stuff'] = logging
        else:
            bucket_info['logging'] = 'Disabled'
        return True
    except Exception as e:
        print_error('Failed to get logging configuration for %s: %s' % (bucket_name, e))
        bucket_info['logging'] = 'Unknown'
        return False


# noinspection PyBroadException
def get_s3_bucket_webhosting(api_client, bucket_name, bucket_info):
    try:
        result = api_client.get_bucket_website(Bucket=bucket_name)
        bucket_info['web_hosting_enabled'] = 'IndexDocument' in result
        return True
    except Exception:
        # TODO: distinguish permission denied from  'NoSuchWebsiteConfiguration' errors
        bucket_info['web_hosting_enabled'] = False
        return False


def get_s3_bucket_default_encryption(api_client, bucket_name, bucket_info):
    try:
        default_encryption = api_client.get_bucket_encryption(Bucket=bucket_name)
        bucket_info['default_encryption_enabled'] = True
        return True
    except ClientError as e:
        if 'ServerSideEncryptionConfigurationNotFoundError' in e.response['Error']['Code']:
            bucket_info['default_encryption_enabled'] = False
            return True
        else:
            print_error('Failed to get encryption configuration for %s: %s' % (bucket_name, e))
            bucket_info['default_encryption_enabled'] = None
            return False
    except Exception as e:
        print_error('Failed to get encryption configuration for %s: %s' % (bucket_name, e))
        bucket_info['default_encryption'] = 'Unknown'
        return False


def get_s3_buckets(api_client, s3_info, s3_params):
    """
    List all available buckets

    :param api_client:
    :param s3_info:
    :param s3_params:
    :return:
    """
    manage_dictionary(s3_info, 'buckets', {})
    buckets = api_client[get_s3_list_region(s3_params['selected_regions'])].list_buckets()['Buckets']
    targets = []
    for b in buckets:
        # Abort if bucket is not of interest
        if (b['Name'] in s3_params['skipped_buckets']) or \
                (len(s3_params['checked_buckets']) and b['Name'] not in s3_params['checked_buckets']):
            continue
        targets.append(b)
    s3_info['buckets_count'] = len(targets)
    s3_params['api_clients'] = api_client
    s3_params['s3_info'] = s3_info
    # FIXME - commented for now as this method doesn't seem to be defined anywhere'
    # thread_work(targets, get_s3_bucket, params = s3_params, num_threads = 30)
    # show_status(s3_info)
    s3_info['buckets_count'] = len(s3_info['buckets'])
    return s3_info


def get_s3_bucket_keys(api_client, bucket_name, bucket, check_encryption, check_acls):
    """
    Get key-specific information (server-side encryption, acls, etc...)

    :param api_client:
    :param bucket_name:
    :param bucket:
    :param check_encryption:
    :param check_acls:
    :return:
    """
    bucket['keys'] = []
    keys = handle_truncated_response(api_client.list_objects, {'Bucket': bucket_name}, ['Contents'])
    bucket['keys_count'] = len(keys['Contents'])
    key_count = 0
    # FIXME - commented for now as this method doesn't seem to be defined anywhere'
    # update_status(key_count, bucket['keys_count'], 'keys')
    for key in keys['Contents']:
        key_count += 1
        key['name'] = key.pop('Key')
        key['LastModified'] = str(key['LastModified'])
        if check_encryption:
            try:
                # The encryption configuration is only accessible via an HTTP header,
                # only returned when requesting one object at a time...
                k = api_client.get_object(Bucket=bucket_name, Key=key['name'])
                key['ServerSideEncryption'] = k['ServerSideEncryption'] if 'ServerSideEncryption' in k else None
                key['SSEKMSKeyId'] = k['SSEKMSKeyId'] if 'SSEKMSKeyId' in k else None
            except Exception as e:
                print_exception(e)
                continue
        if check_acls:
            # noinspection PyBroadException
            try:
                key['grantees'] = get_s3_acls(api_client, bucket_name, bucket, key_name=key['name'])
            except Exception:
                continue
        # Save it
        bucket['keys'].append(key)


def get_s3_list_region(region):
    """
    Return region to be used for global calls such as list bucket and get bucket location

    :param region:
    :return:
    """
    if region.startswith('us-gov-'):
        return 'us-gov-west-1'
    elif region.startswith('cn-'):
        return 'cn-north-1'
    else:
        return region


def get_s3_bucket_location(s3_client, bucket_name):
    """

    :param s3_client:
    :param bucket_name:
    :return:
    """
    location = s3_client.get_bucket_location(Bucket=bucket_name)
    return location['LocationConstraint'] if location['LocationConstraint'] else 'us-east-1'
