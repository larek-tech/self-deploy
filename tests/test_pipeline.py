from larek.models.repo import (
    RepoSchema,
    Service,
    Language,
    Dependencies,
    Lib,
    Docker,
)
from larek.pipeliner.builder import PipelineComposer
from pathlib import Path

# Create two sample services
service_java = Service(
    path=Path("service-a"),
    name="service-a",
    lang=Language(name="java", version="17"),
    dependencies=Dependencies(
        packet_manager="maven",
        libs=[Lib(name="org.springframework:spring-core", version="5.3.10")],
    ),
    configs=[],
    docker=Docker(dockerfiles=["service-a/Dockerfile"], compose=None, environment=[]),
    entrypoints=[],
    tests="mvn test",
    linters=[],
    android=None,
)

service_node = Service(
    path=Path("service-b"),
    name="service-b",
    lang=Language(name="javascript", version="20"),
    dependencies=Dependencies(
        packet_manager="npm", libs=[Lib(name="react", version="18.2.0")]
    ),
    configs=[],
    docker=Docker(dockerfiles=[], compose=None, environment=[]),
    entrypoints=[],
    tests="npm test",
    linters=[],
    android=None,
)

schema = RepoSchema(
    is_monorepo=True, services=[service_java, service_node], deployment=None
)

composer = PipelineComposer()
print(composer.generate_from_schema(schema))
