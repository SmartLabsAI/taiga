# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

import logging
from typing import List

from fastapi import Query
from fastapi.params import Depends
from taiga.auth.routing import AuthAPIRouter
from taiga.base.api import Request
from taiga.base.api.permissions import check_permissions
from taiga.exceptions import api as ex
from taiga.exceptions import services as services_ex
from taiga.exceptions.api.errors import ERROR_403, ERROR_404, ERROR_422
from taiga.permissions import HasPerm, IsProjectAdmin
from taiga.projects import services as projects_services
from taiga.projects.models import Project
from taiga.projects.serializers import ProjectSerializer, ProjectSummarySerializer
from taiga.projects.validators import PermissionsValidator, ProjectValidator
from taiga.users.models import Role
from taiga.users.serializers import RoleSerializer
from taiga.workspaces import services as workspaces_services

logger = logging.getLogger(__name__)

metadata = {
    "name": "projects",
    "description": "Endpoint for projects resources.",
}

router = AuthAPIRouter(prefix="/projects", tags=["projects"])
router_workspaces = AuthAPIRouter(prefix="/workspaces/{workspace_slug}/projects", tags=["workspaces"])

# PERMISSIONS
LIST_PROJECTS = HasPerm("view_workspace")
CREATE_PROJECT = HasPerm("view_workspace")
GET_PROJECT = HasPerm("view_project")
GET_PROJECT_ROLES = IsProjectAdmin()
UPDATE_PROJECT_ROLE_PERMISSIONS = IsProjectAdmin()


@router_workspaces.get(
    "",
    name="projects.list",
    summary="List projects",
    response_model=List[ProjectSummarySerializer],
    responses=ERROR_422 | ERROR_403,
)
def list_projects(
    request: Request, workspace_slug: str = Query("", description="the workspace slug (str)")
) -> List[ProjectSerializer]:
    """
    List projects of a workspace visible by the user.
    """
    workspace = workspaces_services.get_workspace(slug=workspace_slug)
    if workspace is None:
        logger.exception(f"Workspace {workspace_slug} does not exist")
        raise ex.NotFoundError()

    # TODO - revisar esto porque no está bien.
    # también tendría que devolver proyectos en los que eres miembro
    # pero no eres miembro del WS y ahí no vas a tener permiso de view_workspace
    check_permissions(permissions=LIST_PROJECTS, user=request.user, obj=workspace)

    # TODO - sólo debería mostrar los proyectos visibles por el usuario dentro del workspace
    projects = projects_services.get_projects(workspace_slug=workspace_slug)
    return ProjectSerializer.from_queryset(projects)


@router.post(
    "",
    name="projects.create",
    summary="Create project",
    response_model=ProjectSerializer,
    responses=ERROR_422 | ERROR_403,
)
def create_project(
    request: Request,
    form: ProjectValidator = Depends(ProjectValidator.as_form),  # type: ignore[assignment, attr-defined]
) -> ProjectSerializer:
    """
    Create project for the logged user in a given workspace.
    """
    workspace = workspaces_services.get_workspace(slug=form.workspace_slug)

    check_permissions(permissions=CREATE_PROJECT, user=request.user, obj=workspace)

    project = projects_services.create_project(
        workspace=workspace,
        name=form.name,
        description=form.description,
        color=form.color,
        owner=request.user,
        logo=form.logo,
    )

    return ProjectSerializer.from_orm(project)


@router.get(
    "/{slug}",
    name="projects.get",
    summary="Get project",
    response_model=ProjectSerializer,
    responses=ERROR_404 | ERROR_422 | ERROR_403,
)
def get_project(request: Request, slug: str = Query("", description="the project slug (str)")) -> ProjectSerializer:
    """
    Get project detail by slug.
    """

    project = _get_project_or_404(slug)
    check_permissions(permissions=GET_PROJECT, user=request.user, obj=project)
    return ProjectSerializer.from_orm(project)


@router.get(
    "/{slug}/roles",
    name="project.permissions.get",
    summary="Get project roles permissions",
    response_model=List[RoleSerializer],
    responses=ERROR_404 | ERROR_422 | ERROR_403,
)
def get_project_roles(
    request: Request, slug: str = Query(None, description="the project slug (str)")
) -> List[RoleSerializer]:
    """
    Get project roles and permissions
    """

    project = _get_project_or_404(slug)
    check_permissions(permissions=GET_PROJECT_ROLES, user=request.user, obj=project)
    roles_permissions = projects_services.get_roles_permissions(project=project)
    return RoleSerializer.from_queryset(roles_permissions)


@router.put(
    "/{slug}/roles/{role_slug}/permissions",
    name="project.permissions.put",
    summary="Edit project roles permissions",
    response_model=RoleSerializer,
    responses=ERROR_404 | ERROR_422 | ERROR_403,
)
def update_project_role_permissions(
    request: Request,
    form: PermissionsValidator,
    slug: str = Query(None, description="the project slug (str)"),
    role_slug: str = Query(None, description="the role slug (str)"),
) -> RoleSerializer:
    """
    Edit project roles permissions
    """

    project = _get_project_or_404(slug)
    check_permissions(permissions=UPDATE_PROJECT_ROLE_PERMISSIONS, user=request.user, obj=project)
    role = _get_project_role_or_404(project=project, slug=role_slug)

    try:
        role = projects_services.update_role_permissions(role, form.permissions)
        return RoleSerializer.from_orm(role)
    except services_ex.NonEditableRoleError:
        logger.exception("Cannot edit permissions in an admin role")
        raise ex.ForbiddenError("Cannot edit permissions in an admin role")
    except services_ex.BadPermissionsSetError:
        logger.exception("Given permissions are incompatible")
        raise ex.BadRequest("Given permissions are incompatible")


def _get_project_or_404(slug: str) -> Project:
    project = projects_services.get_project(slug=slug)
    if project is None:
        logger.exception(f"Project {slug} does not exist")
        raise ex.NotFoundError()

    return project


def _get_project_role_or_404(project: Project, slug: str) -> Role:
    role = projects_services.get_project_role(project=project, slug=slug)
    if role is None:
        logger.exception(f"Role {slug} does not exist")
        raise ex.NotFoundError()

    return role
