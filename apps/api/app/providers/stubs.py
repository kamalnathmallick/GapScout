"""Stubs for future data source providers (Google Places API and CSV import)."""

from app.providers.base import DataSourceProvider, PlaceDTO, RawPlace, SearchOptions


class GooglePlacesApiProvider(DataSourceProvider):
    """Stub provider for the official Google Places API (New).

    TODO(Prompt 17/commercial): Implement official Google Places API provider:
      1. Use google-maps-services-python or direct REST /v1/places:searchNearby
      2. Authenticate using GOOGLE_MAPS_API_KEY from environment
      3. Field masking to minimize billing (displayName, formattedAddress, rating,
         userRatingCount, etc.)
      4. Place Details requests for opening hours and reviews if needed
      5. Transform upstream JSON to PlaceDTO
    """

    @property
    def name(self) -> str:
        return "google_places_api"

    def search(
        self,
        category: str,
        area_or_cell: str,
        options: SearchOptions | None = None,
    ) -> list[RawPlace]:
        raise NotImplementedError(
            "GooglePlacesApiProvider is not yet implemented. "
            "Use GosomScraperProvider for scraping or CsvImportProvider for offline datasets."
        )

    def to_place_dto(self, raw: RawPlace) -> PlaceDTO:
        raise NotImplementedError("GooglePlacesApiProvider.to_place_dto is not yet implemented.")


class CsvImportProvider(DataSourceProvider):
    """Stub provider for importing pre-scraped or customer-supplied CSV files.

    TODO: Implement offline CSV import:
      1. Accept file path or stream from area_or_cell / options
      2. Auto-detect CSV dialects and column headers
      3. Map columns defensively to RawPlace and PlaceDTO
      4. Support batch imports for bulk data loading
    """

    @property
    def name(self) -> str:
        return "csv_import"

    def search(
        self,
        category: str,
        area_or_cell: str,
        options: SearchOptions | None = None,
    ) -> list[RawPlace]:
        raise NotImplementedError(
            "CsvImportProvider is not yet implemented. "
            "Use GosomScraperProvider to query the live scraper service."
        )

    def to_place_dto(self, raw: RawPlace) -> PlaceDTO:
        raise NotImplementedError("CsvImportProvider.to_place_dto is not yet implemented.")
