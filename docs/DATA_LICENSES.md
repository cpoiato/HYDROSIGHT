# Data sources, licences and attribution — HYDROSIGHT

Last reviewed: 2026-11-25.

## Scope

HYDROSIGHT's source code is licensed under the [MIT License](../LICENSE). **The MIT License does not relicense third-party data** acquired or generated from the sources listed below. Their original terms remain applicable to raw snapshots, redistributed copies and any data-bearing exports.

This inventory reflects the sources used by the project's `download_calgary_data.py`, `reports/latest_download_manifest.json`, historical weather manifest and `src/hydrosight/preprocessing/spatial_grid.py`. It is not a blanket permission for other datasets, basemaps, imagery or future replacement sources.

## Source inventory

| Dataset in HYDROSIGHT | Publisher and source | Terms and use conditions |
| --- | --- | --- |
| Water main breaks (dataset `dpcu-jr23`) | City of Calgary — [dataset](https://data.calgary.ca/d/dpcu-jr23) | [Open Government Licence – City of Calgary](https://data.calgary.ca/stories/s/u45n-7awa/); attribution and non-endorsement required; check dataset metadata for exclusions |
| Public water mains (dataset `w6h9-w33i`) | City of Calgary — [dataset](https://data.calgary.ca/d/w6h9-w33i) | Same Calgary open-data terms; attribution and non-endorsement |
| Hospitals (ArcGIS `Hospital/FeatureServer/0`) | City of Calgary — [service](https://services1.arcgis.com/AVP60cs0Q9PEA8rH/ArcGIS/rest/services/Hospital/FeatureServer/0) | Calgary open-data terms referenced by the municipal service; reconfirm current metadata on refresh |
| Schools (ArcGIS `School/FeatureServer/0`) | City of Calgary — [service](https://services1.arcgis.com/AVP60cs0Q9PEA8rH/ArcGIS/rest/services/School/FeatureServer/0) | Calgary open-data terms explicitly referenced in the service's `copyrightText` |
| City boundary used to derive the 500 m grid | City of Calgary — [ArcGIS City_Boundary](https://services1.arcgis.com/AVP60cs0Q9PEA8rH/ArcGIS/rest/services/City_Boundary/FeatureServer/0) | Calgary open-data terms; retain source attribution for the derived grid |
| Historical daily weather (stations `2205` and `50430`) | Environment and Climate Change Canada (ECCC) — [historical climate archive](https://climate.weather.gc.ca/climate_data/bulk_data_e.html) | [ECCC restricted-use data licence](https://climate.weather.gc.ca/prods_servs/attachment1_f.html); source acknowledgment and redistribution conditions |

## 1. City of Calgary open data

The [Open Government Licence – City of Calgary](https://data.calgary.ca/stories/s/u45n-7awa/) generally permits use, modification, sharing and commercial use under its terms. Obligations include:

- Acknowledge the City as the information provider. Suggested attribution: **"Contains information licensed under the Open Government Licence – City of Calgary."** Include a link to the licence where possible.
- Do not imply City approval, partnership or endorsement of HYDROSIGHT or its predictions.
- Observe exclusions for third-party intellectual property, personal information, official marks and other rights outside the licence.
- Check each source's metadata and applicable terms when refreshing the collection. The City open-data licence should not be confused with separate commercial data products or general website terms.

## 2. ECCC historical climate archive

The archive directly used by this project links to ECCC's [restricted-use data agreement](https://climate.weather.gc.ca/prods_servs/attachment1_f.html). Under that agreement:

- Use is granted subject to its restrictions and without a transfer of the underlying intellectual property rights.
- Credit ECCC. Suggested attribution: **"Created using data from Environment and Climate Change Canada."**
- Redistribution of source data, including portions, requires notifying recipients of the source terms **and obtaining their acceptance**.
- Do not charge specifically for redistributed ECCC data. The agreement permits charging for value-added services under its conditions.
- If a proposed use or redistribution is not covered, obtain clarification or written authorization from ECCC as appropriate.
- Do not assume that the general Open Government Licence – Canada or licences for other ECCC download services automatically supersede the archive-specific agreement.

These conditions are relevant to public data bundles, APIs returning raw climate records, dataset exports and sharing a remote data store. A paid service that only displays model outputs must still be reviewed for whether it redistributes any ECCC data.

## 3. Requirements for the project

1. Preserve source URL, publisher, dataset ID or station ID, collection timestamp, version/hash and the applicable licence link alongside each collected snapshot.
2. Show appropriate City of Calgary and ECCC credits in the future website and on exported reports or data extracts, when the relevant sources are used.
3. Keep source datasets and their licence notices distinct from the MIT-licensed application code. Do not label all DVC-backed data as MIT.
4. Before publishing raw or substantially reconstructed ECCC data in GitHub, a public DVC remote, a downloadable file or an API, verify all recipient-notification and acceptance conditions and the proposed charging model.
5. Do not reproduce third-party logos or imply official approval by Calgary or ECCC.
6. Review licence terms again if datasets, platforms, delivery method, or the intended commercial use changes.

## 4. Status and follow-up

- **Current academic research and internal model training:** compatible in principle with the identified licences if their conditions are observed. No separate paid-data licence has been identified for the sources reviewed.
- **Public application displaying predictions without redistributing source data:** generally lower licensing risk; maintain attribution and verify exact displayed content.
- **Commercial distribution of underlying ECCC records:** **review required before release**; compliance with the restricted agreement (and potentially ECCC clarification) is not assumed.
- **Other map tiles or third-party basemaps:** not included in this inventory. Check those providers' conditions before adding them to the interface.
- **Legal status:** a documented source-by-source review, not legal advice or an official permission letter from the publishers.

## Official references

- [Open Calgary — Open Government Licence / Terms of Use](https://data.calgary.ca/stories/s/u45n-7awa/)
- [ECCC — Historical Climate Data](https://climate.weather.gc.ca/)
- [ECCC — Licence Agreement for Use of Data](https://climate.weather.gc.ca/prods_servs/attachment1_f.html)
- [HYDROSIGHT collection manifest](../reports/latest_download_manifest.json)
