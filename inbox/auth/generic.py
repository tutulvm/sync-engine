import datetime
import socket

import attr
from imapclient import IMAPClient
from nylas.logging import get_logger

from inbox.auth.utils import auth_is_invalid, auth_requires_app_password
from inbox.basicauth import AppPasswordError, ValidationError
from inbox.models import Namespace
from inbox.models.backends.generic import GenericAccount

from .base import AuthHandler
from .utils import create_imap_connection

log = get_logger()


@attr.s
class GenericAccountData(object):
    email = attr.ib()

    imap_server_host = attr.ib()
    imap_server_port = attr.ib()
    imap_username = attr.ib()
    imap_password = attr.ib()

    smtp_server_host = attr.ib()
    smtp_server_port = attr.ib()
    smtp_username = attr.ib()
    smtp_password = attr.ib()

    sync_email = attr.ib()


class GenericAuthHandler(AuthHandler):
    def create_account(self, account_data):
        namespace = Namespace()
        account = GenericAccount(namespace=namespace)
        account.provider = "custom"
        account.create_emailed_events_calendar()
        return self.update_account(account, account_data)

    def update_account(self, account, account_data):
        account.email_address = account_data.email

        account.imap_endpoint = (
            account_data.imap_server_host,
            account_data.imap_server_port,
        )

        account.smtp_endpoint = (
            account_data.smtp_server_host,
            account_data.smtp_server_port,
        )

        account.imap_username = account_data.imap_username
        account.imap_password = account_data.imap_username

        account.smtp_username = account_data.smtp_username
        account.smtp_password = account_data.smtp_username

        account.date = datetime.datetime.utcnow()

        account.ssl_required = True
        account.sync_email = account_data.sync_email

        return account

    def authenticate_imap_connection(self, account, conn):
        try:
            conn.login(account.imap_username, account.imap_password)
        except IMAPClient.Error as exc:
            if auth_is_invalid(exc):
                log.error(
                    "IMAP login failed", account_id=account.id, error=exc,
                )
                raise ValidationError(exc)
            elif auth_requires_app_password(exc):
                raise AppPasswordError(exc)
            else:
                log.error(
                    "IMAP login failed for an unknown reason. Check auth_is_invalid",
                    account_id=account.id,
                    error=exc,
                )
                raise

    def get_imap_connection(self, account, use_timeout=True):
        host, port = account.imap_endpoint
        ssl_required = account.ssl_required
        try:
            return create_imap_connection(host, port, ssl_required, use_timeout)
        except (IMAPClient.Error, socket.error) as exc:
            log.error(
                "Error instantiating IMAP connection", account_id=account.id, error=exc,
            )
            raise
