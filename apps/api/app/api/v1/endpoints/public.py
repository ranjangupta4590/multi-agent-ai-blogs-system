"""Safe unauthenticated delivery of published articles only."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.errors import ForbiddenError
from app.core.rate_limit import enforce_rate_limit
from app.schemas.schemas import CommentCreate, CommentUpdate
from app.services.auth_service import get_current_user
from app.models.entities import Article, Comment, Organization, Project, User

router = APIRouter()


def _published_articles_query():
    return (
        select(Article, Organization)
        .join(Project, Article.project_id == Project.id)
        .join(Organization, Project.organization_id == Organization.id)
        .where(Article.status == "PUBLISHED", Project.is_archived.is_(False))
    )


def _summary(article: Article, organization: Organization) -> dict:
    return {
        "id": article.id,
        "organization_name": organization.name,
        "organization_slug": organization.slug,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "target_keywords": article.target_keywords,
        "estimated_reading_time": article.estimated_reading_time,
        "word_count": article.word_count,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


@router.get("/articles")
async def list_published_articles(
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Public home feed. No draft or internal workflow data is exposed."""
    result = await db.execute(
        _published_articles_query().order_by(Article.updated_at.desc()).offset(offset).limit(limit)
    )
    return [_summary(article, organization) for article, organization in result.all()]


@router.get("/organizations/{organization_slug}/articles/{article_id}/{slug}")
async def get_published_article(
    organization_slug: str,
    article_id: str,
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Public reader route scoped to a published article and its organization."""
    result = await db.execute(
        _published_articles_query().where(
            Organization.slug == organization_slug,
            Article.id == article_id,
            Article.slug == slug,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Published article not found.")

    article, organization = row
    return {**_summary(article, organization), "content": article.content}

def _comment_payload(comment: Comment, author: User) -> dict:
    return {
        "id": comment.id,
        "article_id": comment.article_id,
        "author_id": comment.author_id,
        "author_name": author.full_name,
        "content": comment.content,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }


async def _require_published_article(article_id: str, db: AsyncSession) -> Article:
    result = await db.execute(
        select(Article)
        .join(Project, Article.project_id == Project.id)
        .where(Article.id == article_id, Article.status == "PUBLISHED", Project.is_archived.is_(False))
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Published article not found.")
    return article


@router.get("/articles/{article_id}/comments")
async def list_public_comments(article_id: str, db: AsyncSession = Depends(get_db)):
    await _require_published_article(article_id, db)
    result = await db.execute(
        select(Comment, User)
        .join(User, Comment.author_id == User.id)
        .where(Comment.article_id == article_id)
        .order_by(Comment.created_at.asc())
    )
    return [_comment_payload(comment, author) for comment, author in result.all()]


@router.post("/articles/{article_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_public_comment(
    article_id: str,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_published_article(article_id, db)
    enforce_rate_limit(f"comment_create_{current_user.id}", max_requests=10, window_seconds=60)
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Comment cannot be blank.")
    comment = Comment(article_id=article_id, author_id=current_user.id, content=content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return _comment_payload(comment, current_user)


async def _get_moderatable_comment(article_id: str, comment_id: str, db: AsyncSession) -> Comment:
    await _require_published_article(article_id, db)
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.article_id == article_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found.")
    return comment


def _can_moderate_comment(comment: Comment, user: User) -> bool:
    return comment.author_id == user.id or user.role in {"SUPER_ADMIN", "ADMIN"}


@router.put("/articles/{article_id}/comments/{comment_id}")
async def update_public_comment(
    article_id: str,
    comment_id: str,
    req: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await _get_moderatable_comment(article_id, comment_id, db)
    if not _can_moderate_comment(comment, current_user):
        raise ForbiddenError("You can edit only your own comments.")
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Comment cannot be blank.")
    comment.content = content
    await db.commit()
    await db.refresh(comment)
    author_result = await db.execute(select(User).where(User.id == comment.author_id))
    return _comment_payload(comment, author_result.scalar_one())


@router.delete("/articles/{article_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_public_comment(
    article_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await _get_moderatable_comment(article_id, comment_id, db)
    if not _can_moderate_comment(comment, current_user):
        raise ForbiddenError("You can delete only your own comments.")
    await db.delete(comment)
    await db.commit()
