"""Tests for place upsert idempotency and database persistence."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Place, PlaceReview, Workspace
from app.providers.base import PlaceDTO, ReviewDTO
from app.services.places import upsert_places


def test_upsert_places_idempotency_and_no_duplicates(db_engine) -> None:
    with Session(db_engine) as session:
        ws = Workspace(name="Upsert Test Workspace")
        session.add(ws)
        session.commit()
        workspace_id = ws.id

        dto = PlaceDTO(
            provider="gosom",
            provider_place_id="unique_cafe_001",
            name="Indiranagar Specialty Coffee",
            category="Cafe",
            address="100ft Road, Indiranagar",
            phone="+919876543210",
            website="https://specialtycoffee.example.com",
            email="hello@specialtycoffee.example.com",
            rating=4.6,
            review_count=150,
            price_level=2,
            latitude=12.9784,
            longitude=77.6408,
            is_closed=False,
            raw={"sample_field": "untouched_value", "nested": {"key": 1}},
            reviews=[
                ReviewDTO(
                    author_name="Priya M",
                    rating=5,
                    text="Best pour over in town!",
                    owner_replied=True,
                )
            ],
        )

        # 1. First run: place is created
        place_ids = upsert_places(session, workspace_id, [dto])
        assert len(place_ids) == 1
        first_id = place_ids[0]

        # Verify initial database state
        place = session.execute(select(Place).where(Place.id == first_id)).scalar_one()
        assert place.name == "Indiranagar Specialty Coffee"
        assert place.review_count == 150
        assert place.raw == {"sample_field": "untouched_value", "nested": {"key": 1}}

        # Verify review created
        reviews = (
            session.execute(select(PlaceReview).where(PlaceReview.place_id == first_id))
            .scalars()
            .all()
        )
        assert len(reviews) == 1
        assert reviews[0].review_text == "Best pour over in town!"
        assert reviews[0].rating == 5
        assert reviews[0].owner_replied is True

        # 2. Re-running with updated fields (e.g. review_count increased to 160)
        updated_dto = dto.model_copy(
            update={
                "review_count": 160,
                "rating": 4.7,
                "raw": {"sample_field": "updated_untouched_value"},
            }
        )
        second_place_ids = upsert_places(session, workspace_id, [updated_dto])
        assert len(second_place_ids) == 1
        assert second_place_ids[0] == first_id  # Same record ID, no duplicate created

        # Total places count in workspace must still be exactly 1
        count = session.execute(
            select(func.count()).select_from(Place).where(Place.workspace_id == workspace_id)
        ).scalar_one()
        assert count == 1

        # Verify updated values on the existing record
        session.expire_all()
        updated_place = session.execute(select(Place).where(Place.id == first_id)).scalar_one()
        assert updated_place.review_count == 160
        assert updated_place.rating == 4.7
        assert updated_place.raw == {"sample_field": "updated_untouched_value"}

        # Verify reviews are NOT duplicated after re-running upsert
        reviews_after = (
            session.execute(select(PlaceReview).where(PlaceReview.place_id == first_id))
            .scalars()
            .all()
        )
        assert len(reviews_after) == 1
        assert reviews_after[0].review_text == "Best pour over in town!"

        # 3. Third run: passing multiple duplicate review objects in the list
        duplicate_reviews_dto = dto.model_copy(
            update={
                "reviews": [
                    ReviewDTO(author_name="Priya M", rating=5, text="Duplicate review"),
                    ReviewDTO(author_name="Priya M", rating=5, text="Duplicate review"),
                ]
            }
        )
        upsert_places(session, workspace_id, [duplicate_reviews_dto])
        reviews_deduped = (
            session.execute(select(PlaceReview).where(PlaceReview.place_id == first_id))
            .scalars()
            .all()
        )
        assert len(reviews_deduped) == 1
        assert reviews_deduped[0].review_text == "Duplicate review"


def test_upsert_places_workspace_isolation(db_engine) -> None:
    with Session(db_engine) as session:
        ws1 = Workspace(name="Workspace A")
        ws2 = Workspace(name="Workspace B")
        session.add_all([ws1, ws2])
        session.commit()

        dto = PlaceDTO(
            provider="gosom",
            provider_place_id="shared_provider_id",
            name="Shared Name Cafe",
        )

        id1 = upsert_places(session, ws1.id, [dto])[0]
        id2 = upsert_places(session, ws2.id, [dto])[0]

        # Different workspaces allow the same provider_place_id as distinct records
        assert id1 != id2
