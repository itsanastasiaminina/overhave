import logging
from http import HTTPStatus
from typing import cast

from gitlab import GitlabCreateError, GitlabHttpError
from gitlab.v4.objects.merge_requests import ProjectMergeRequest

from overhave.entities import OverhaveFileSettings, PublisherContext
from overhave.publication.git_publisher import GitVersionPublisher
from overhave.publication.gitlab.settings import OverhaveGitlabPublisherSettings
from overhave.publication.gitlab.tokenizer.client import TokenizerClient
from overhave.scenario import FileManager
from overhave.storage import IDraftStorage, IFeatureStorage, IScenarioStorage, ITestRunStorage
from overhave.test_execution import OverhaveProjectSettings
from overhave.transport.http.gitlab_client import GitlabHttpClient, GitlabMrRequest
from overhave.transport.http.gitlab_client.models import GitlabMrCreationResponse

logger = logging.getLogger(__name__)


class GitlabVersionPublisher(GitVersionPublisher):
    """ Class for feature version's merge requests management relative to Gitlab API. """

    def __init__(
        self,
        file_settings: OverhaveFileSettings,
        project_settings: OverhaveProjectSettings,
        feature_storage: IFeatureStorage,
        scenario_storage: IScenarioStorage,
        test_run_storage: ITestRunStorage,
        draft_storage: IDraftStorage,
        file_manager: FileManager,
        gitlab_publisher_settings: OverhaveGitlabPublisherSettings,
        gitlab_client: GitlabHttpClient,
        tokenizer_client: TokenizerClient,
    ):
        super().__init__(
            file_settings=file_settings,
            project_settings=project_settings,
            feature_storage=feature_storage,
            scenario_storage=scenario_storage,
            test_run_storage=test_run_storage,
            draft_storage=draft_storage,
            file_manager=file_manager,
        )
        self._gitlab_publisher_settings = gitlab_publisher_settings
        self._gitlab_client = gitlab_client
        self._tokenizer_client = tokenizer_client

    def publish_version(self, draft_id: int) -> None:
        logger.info("Start processing draft_id=%s...", draft_id)
        context = self._push_version(draft_id)
        if not isinstance(context, PublisherContext):
            return
        merge_request = GitlabMrRequest(
            project_id=self._gitlab_publisher_settings.repository_id,
            title=context.feature.name,
            source_branch=context.target_branch,
            target_branch=self._gitlab_publisher_settings.target_branch,
            description=self._compile_publication_description(context),
            reviewer_ids=self._gitlab_publisher_settings.get_reviewers(feature_type=context.feature.feature_type.name),
        )
        logger.info("Prepared merge-request: %s", merge_request.json(by_alias=True))
        try:
            token = None
            if self._tokenizer_client._settings.enabled:
                token = self._tokenizer_client.get_token(draft_id=draft_id).token
            response = self._gitlab_client.send_merge_request(
                merge_request=merge_request, token=token, repository_id=self._gitlab_publisher_settings.repository_id
            )
            if isinstance(response, ProjectMergeRequest):
                parsed_response = cast(GitlabMrCreationResponse, response.attributes)
                self._draft_storage.save_response(
                    draft_id=draft_id,
                    pr_url=parsed_response.web_url,  # type: ignore
                    published_at=parsed_response.created_at,
                    opened=parsed_response.state == "opened",
                )
                return
        except (GitlabCreateError, GitlabHttpError) as e:
            if e.response_code == HTTPStatus.CONFLICT:
                logger.exception("Gotten conflict. Try to return last merge-request for Draft with id=%s...", draft_id)
                self._save_as_duplicate(context)
                return
            logger.exception("Got HTTP error while trying to sent merge-request!")
