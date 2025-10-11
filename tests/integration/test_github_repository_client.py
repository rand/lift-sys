from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from git import Repo

from lift_sys.auth.token_store import TokenStore
from lift_sys.services.github_repository import (
    GitHubRepositoryClient,
    RepositoryAccessError,
)


def _create_remote_repo(directory: Path) -> Repo:
    repo = Repo.init(directory)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Test User")
        writer.set_value("user", "email", "test@example.com")
    (directory / "README.md").write_text("hello", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return repo


def _mock_transport(remote_path: Path) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/octocat/example":
            return httpx.Response(
                200,
                json={
                    "full_name": "octocat/example",
                    "name": "example",
                    "owner": {"login": "octocat"},
                    "description": "Example repository",
                    "default_branch": "main",
                    "private": False,
                    "clone_url": str(remote_path),
                },
            )
        if request.url.path == "/user/repos":
            return httpx.Response(
                200,
                json=[
                    {
                        "full_name": "octocat/example",
                        "name": "example",
                        "owner": {"login": "octocat"},
                        "description": "Example repository",
                        "default_branch": "main",
                        "private": False,
                    }
                ],
            )
        return httpx.Response(404, json={"message": "not found"})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_ensure_repository_clones_workspace(tmp_path: Path) -> None:
    remote_repo_path = tmp_path / "remote"
    _create_remote_repo(remote_repo_path)

    token_store = TokenStore({}, TokenStore.generate_key())
    token_store.save_tokens("user", "github", {"access_token": "token123"})

    transport = _mock_transport(remote_repo_path)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")
    client = GitHubRepositoryClient(
        token_store,
        workspace_root=tmp_path / "workspace",
        http_client=http_client,
    )

    metadata = await client.ensure_repository("user", "octocat/example")

    repo = Repo(metadata.workspace_path)
    assert repo.working_tree_dir is not None
    assert (Path(repo.working_tree_dir) / "README.md").exists()
    assert metadata.identifier == "octocat/example"

    await client.aclose()


@pytest.mark.asyncio
async def test_ensure_repository_updates_existing_clone(tmp_path: Path) -> None:
    remote_repo_path = tmp_path / "remote"
    repo = _create_remote_repo(remote_repo_path)

    token_store = TokenStore({}, TokenStore.generate_key())
    token_store.save_tokens("user", "github", {"access_token": "token123"})

    transport = _mock_transport(remote_repo_path)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")
    client = GitHubRepositoryClient(
        token_store,
        workspace_root=tmp_path / "workspace",
        http_client=http_client,
    )

    metadata = await client.ensure_repository("user", "octocat/example")
    local_repo = Repo(metadata.workspace_path)
    assert "README.md" in local_repo.git.ls_files()

    (remote_repo_path / "CHANGELOG.md").write_text("updates", encoding="utf-8")
    repo.index.add(["CHANGELOG.md"])
    repo.index.commit("update changelog")

    metadata = await client.ensure_repository("user", "octocat/example")
    local_repo = Repo(metadata.workspace_path)
    assert "CHANGELOG.md" in local_repo.git.ls_files()

    await client.aclose()


@pytest.mark.asyncio
async def test_list_repositories_returns_summaries(tmp_path: Path) -> None:
    remote_repo_path = tmp_path / "remote"
    _create_remote_repo(remote_repo_path)

    token_store = TokenStore({}, TokenStore.generate_key())
    token_store.save_tokens("user", "github", {"access_token": "token123"})

    transport = _mock_transport(remote_repo_path)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")
    client = GitHubRepositoryClient(
        token_store,
        workspace_root=tmp_path / "workspace",
        http_client=http_client,
    )

    summaries = await client.list_repositories("user")
    assert len(summaries) == 1
    assert summaries[0].identifier == "octocat/example"

    await client.aclose()


@pytest.mark.asyncio
async def test_ensure_repository_requires_token(tmp_path: Path) -> None:
    token_store = TokenStore({}, TokenStore.generate_key())
    transport = _mock_transport(tmp_path)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")
    client = GitHubRepositoryClient(
        token_store,
        workspace_root=tmp_path / "workspace",
        http_client=http_client,
    )

    with pytest.raises(RepositoryAccessError) as exc:
        await client.ensure_repository("missing", "octocat/example")
    assert exc.value.status_code == 403

    await client.aclose()
