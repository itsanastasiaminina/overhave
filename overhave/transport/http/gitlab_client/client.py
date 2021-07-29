import logging
from typing import Any, Optional

from overhave.transport.http import BaseHttpClient
from overhave.transport.http.base_client import BaseHttpClientException
from overhave.transport.http.gitlab_client.models import GitlabMrRequest
from overhave.transport.http.gitlab_client.settings import OverhaveGitlabClientSettings
from overhave.transport.http.gitlab_client.utils import get_gitlab_python_client

logger = logging.getLogger(__name__)


class BaseGitlabHttpClientException(BaseHttpClientException):
    """ Base exception for :class:`GitlabHttpClient`. """


class GitlabHttpClientConflictError(BaseGitlabHttpClientException):
    """ Exception for situation with `HTTPStatus.CONFLICT` response.status_code. """


class GitlabInvalidTokenError(BaseGitlabHttpClientException):
    """ Exception for situation with invalid token or gitlab url. """


class GitlabHttpClient(BaseHttpClient[OverhaveGitlabClientSettings]):
    """ Client for communication with remote Gitlab server. """

    def send_merge_request(
        self, repository_id: str, merge_request: GitlabMrRequest, token: Optional[str] = None
    ) -> Any:
        gitlab_python_client = get_gitlab_python_client(
            url=self._settings.url.human_repr(),
            token_type=self._settings.token_type,
            token=token or self._settings.auth_token,  # type: ignore
        )
        project = gitlab_python_client.projects.get(repository_id, lazy=True)
        try:
            return project.mergerequests.create(merge_request.dict(by_alias=True))
        except Exception as e:
            logging.exception("Please verify your token or URL! Maybe they are invalid")
            raise GitlabInvalidTokenError("Please verify your token or URL! Maybe they are invalid") from e
