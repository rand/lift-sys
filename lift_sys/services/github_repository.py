"""GitHub repository management utilities."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Iterable, Optional

import httpx
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from ..auth.token_store import TokenStore


class RepositoryAccessError(Exception):
    """Raised when repository operations cannot be completed."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(slots=True)
class RepositorySummary:
    identifier: str
    owner: str
    name: str
    description: Optional[str]
    default_branch: str
    private: bool


@dataclass(slots=True)
class RepositoryMetadata(RepositorySummary):
    clone_url: str
    workspace_path: Path
    last_synced: datetime
    source: str = "github"

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "owner": self.owner,
            "name": self.name,
            "description": self.description,
            "default_branch": self.default_branch,
            "private": self.private,
            "clone_url": self.clone_url,
            "workspace_path": str(self.workspace_path),
            "last_synced": self.last_synced.isoformat(),
            "source": self.source,
        }


class GitHubRepositoryClient:
    """Synchronise repositories the authenticated user can access."""

    def __init__(
        self,
        token_store: TokenStore,
        *,
        workspace_root: Path | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token_store = token_store
        root = workspace_root or Path(
            os.getenv("LIFT_SYS_WORKSPACE_ROOT", "~/.cache/lift-sys/repos")
        )
        self.workspace_root = root.expanduser()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self._http_client = http_client
        self._client_lock = asyncio.Lock()

    async def list_repositories(self, user_id: str) -> list[RepositorySummary]:
        """Return repositories the authenticated user can access."""

        token = self._get_token(user_id)
        response = await self._request("GET", "/user/repos", token)
        repos: list[RepositorySummary] = []
        for item in response.json():
            owner = item.get("owner", {}).get("login", "")
            repos.append(
                RepositorySummary(
                    identifier=item.get("full_name", f"{owner}/{item.get('name', '')}"),
                    owner=owner,
                    name=item.get("name", ""),
                    description=item.get("description"),
                    default_branch=item.get("default_branch", "main"),
                    private=bool(item.get("private", False)),
                )
            )
        return repos

    async def ensure_repository(
        self,
        user_id: str,
        identifier: str,
        *,
        branch: str | None = None,
        force_refresh: bool = False,
    ) -> RepositoryMetadata:
        """Clone or update a repository available to the user."""

        token = self._get_token(user_id)
        repo_data = await self._get_repository(identifier, token)
        owner = repo_data.get("owner", {}).get("login", "")
        name = repo_data.get("name", identifier)
        repo_identifier = repo_data.get("full_name", identifier)
        workspace_path = self._workspace_path(repo_identifier)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        target_branch = branch or repo_data.get("default_branch", "main")

        repo = await asyncio.to_thread(
            self._sync_repository,
            repo_data,
            token,
            workspace_path,
            target_branch,
            force_refresh,
        )

        last_synced = datetime.utcnow()
        return RepositoryMetadata(
            identifier=repo_identifier,
            owner=owner,
            name=name,
            description=repo_data.get("description"),
            default_branch=repo_data.get("default_branch", "main"),
            private=bool(repo_data.get("private", False)),
            clone_url=repo_data.get("clone_url", ""),
            workspace_path=Path(repo.working_tree_dir),
            last_synced=last_synced,
        )

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _get_repository(self, identifier: str, token: str) -> dict[str, Any]:
        response = await self._request("GET", f"/repos/{identifier}", token)
        return response.json()

    def _get_token(self, user_id: str) -> str:
        payload = self._token_store.load_tokens(user_id, "github")
        if not payload:
            raise RepositoryAccessError(403, "github_token_missing")
        access_token = payload.get("access_token")
        if not access_token:
            raise RepositoryAccessError(403, "github_token_missing")
        return str(access_token)

    def _workspace_path(self, identifier: str) -> Path:
        parts = identifier.split("/")
        return self.workspace_root.joinpath(*parts)

    async def _request(self, method: str, path: str, token: str) -> httpx.Response:
        client = await self._ensure_client()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        response = await client.request(method, path, headers=headers)
        if response.status_code == 401:
            raise RepositoryAccessError(403, "github_token_invalid")
        if response.status_code == 404:
            raise RepositoryAccessError(404, "repository_not_found")
        response.raise_for_status()
        return response

    async def _ensure_client(self) -> httpx.AsyncClient:
        async with self._client_lock:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(
                    base_url="https://api.github.com", timeout=30.0
                )
            return self._http_client

    def _clone_repository(
        self,
        repo_data: dict[str, Any],
        token: str,
        destination: Path,
        branch: str,
    ) -> Repo:
        clone_url = repo_data.get("clone_url")
        if not clone_url:
            raise RepositoryAccessError(502, "repository_clone_url_missing")
        authenticated = self._authenticated_url(clone_url, token)
        try:
            repo = Repo.clone_from(authenticated, destination, branch=branch)
            if "origin" in repo.remotes:
                repo.remotes.origin.set_url(clone_url)
        except GitCommandError as exc:  # pragma: no cover - git failures
            raise RepositoryAccessError(500, f"clone_failed: {exc}") from exc
        return repo

    def _sync_repository(
        self,
        repo_data: dict[str, Any],
        token: str,
        workspace_path: Path,
        branch: str,
        force_refresh: bool,
    ) -> Repo:
        if workspace_path.exists() and (workspace_path / ".git").exists():
            repo = Repo(workspace_path)
            self._update_repository(repo, repo_data, token, branch, force_refresh)
            return repo
        return self._clone_repository(repo_data, token, workspace_path, branch)

    def _update_repository(
        self,
        repo: Repo,
        repo_data: dict[str, Any],
        token: str,
        branch: str,
        force_refresh: bool,
    ) -> None:
        clone_url = repo_data.get("clone_url")
        if not clone_url:
            raise RepositoryAccessError(502, "repository_clone_url_missing")
        authenticated = self._authenticated_url(clone_url, token)
        try:
            origin = repo.remotes.origin if "origin" in repo.remotes else None
            if origin is None:
                origin = repo.create_remote("origin", authenticated)
            else:
                origin.set_url(authenticated)
            fetch_args: Iterable[str] = () if force_refresh else (branch,)
            origin.fetch(*fetch_args)
            if branch:
                try:
                    repo.git.checkout(branch)
                except GitCommandError:
                    repo.git.checkout("-B", branch, f"origin/{branch}")
                origin.pull(branch)
        except (GitCommandError, InvalidGitRepositoryError) as exc:
            raise RepositoryAccessError(500, f"update_failed: {exc}") from exc
        finally:
            if clone_url and "origin" in repo.remotes:
                repo.remotes.origin.set_url(clone_url)

    def _authenticated_url(self, clone_url: str, token: str) -> str:
        if clone_url.startswith("http://") or clone_url.startswith("https://"):
            prefix = "https://"
            if clone_url.startswith("http://"):
                prefix = "http://"
            stripped = clone_url[len(prefix) :]
            return f"{prefix}x-access-token:{token}@{stripped}"
        return clone_url


__all__ = [
    "GitHubRepositoryClient",
    "RepositoryAccessError",
    "RepositoryMetadata",
    "RepositorySummary",
]
