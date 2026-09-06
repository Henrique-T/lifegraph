# Lightweight AI experiment procedure

GLiNER-only experiments should not keep REF, Neo4j, the frontend, nine REF edge
containers, or the REF dashboard running. They consume memory and add timing
noise without participating in calibration. These commands preserve containers,
named volumes, and data; routine switching never uses `down -v`.

## AI calibration — GLiNER only

From the REF repository, preserve data while releasing memory:

```powershell
docker compose stop
```

From LifeGraph:

```powershell
docker compose stop frontend backend neo4j
docker compose up -d gliner
docker compose exec -T gliner python /evaluation/extraction/run_calibration.py
```

## AI integration boundary

The current backend initializes and requires Neo4j, so its smallest supported
integration topology is GLiNER + backend + Neo4j:

```powershell
docker compose stop frontend
docker compose up -d neo4j gliner backend
```

## LifeGraph core — no AI and no REF requirement

```powershell
docker compose stop gliner
docker compose up -d neo4j backend frontend
```

## Full demo

From REF:

```powershell
docker compose start
```

From LifeGraph:

```powershell
docker compose up -d neo4j gliner backend frontend
```

`docker compose stop` and `docker compose start` preserve volumes. Never use
`docker compose down -v` for profile switching.
