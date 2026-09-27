"""Catalog of recognizable technologies and of possible migration targets.

It is product data, not a measurement: it lists what can be recognized (by dependencies, images or
extensions) and between which technologies of the same kind a migration can be proposed. Nothing here
claims that a project uses a technology: `stack_scan` decides that with evidence (file and line).
"""

from dataclasses import dataclass, field

Kind = str  # language | backend | frontend | database | orm | infra | testing | build


@dataclass(frozen=True)
class Tech:
    id: str
    name: str
    kind: Kind
    language: str | None = None  # id of the ecosystem's language (None when agnostic)
    icon: str | None = None  # simple-icons slug for the interface
    # Package names per ecosystem that reveal the technology (lowercase).
    packages: dict[str, tuple[str, ...]] = field(default_factory=dict)
    images: tuple[str, ...] = ()  # Docker image names (postgres, redis...)


def _t(id: str, name: str, kind: Kind, language: str | None = None, icon: str | None = None,
       pip: tuple[str, ...] = (), npm: tuple[str, ...] = (), maven: tuple[str, ...] = (),
       go: tuple[str, ...] = (), nuget: tuple[str, ...] = (), composer: tuple[str, ...] = (),
       gem: tuple[str, ...] = (), cargo: tuple[str, ...] = (), images: tuple[str, ...] = ()) -> Tech:
    packages = {k: v for k, v in {"pip": pip, "npm": npm, "maven": maven, "go": go, "nuget": nuget,
                                  "composer": composer, "gem": gem, "cargo": cargo}.items() if v}
    return Tech(id, name, kind, language, icon or id, packages, images)


TECHS: tuple[Tech, ...] = (
    # Languages (detected by extension, not by dependencies)
    _t("python", "Python", "language", "python", "python"),
    _t("javascript", "JavaScript", "language", "javascript", "javascript"),
    _t("typescript", "TypeScript", "language", "typescript", "typescript"),
    _t("java", "Java", "language", "java", "openjdk"),
    _t("kotlin", "Kotlin", "language", "kotlin", "kotlin"),
    _t("csharp", "C#", "language", "csharp", "dotnet"),
    _t("go", "Go", "language", "go", "go"),
    _t("php", "PHP", "language", "php", "php"),
    _t("ruby", "Ruby", "language", "ruby", "ruby"),
    _t("rust", "Rust", "language", "rust", "rust"),
    # Backend
    _t("flask", "Flask", "backend", "python", "flask", pip=("flask",)),
    _t("django", "Django", "backend", "python", "django", pip=("django",)),
    _t("fastapi", "FastAPI", "backend", "python", "fastapi", pip=("fastapi",)),
    _t("express", "Express", "backend", "javascript", "express", npm=("express",)),
    _t("fastify", "Fastify", "backend", "javascript", "fastify", npm=("fastify",)),
    _t("nestjs", "NestJS", "backend", "typescript", "nestjs", npm=("@nestjs/core",)),
    _t("koa", "Koa", "backend", "javascript", "koa", npm=("koa",)),
    _t("spring-boot", "Spring Boot", "backend", "java", "springboot",
       maven=("spring-boot-starter", "spring-boot-starter-web", "spring-boot")),
    _t("quarkus", "Quarkus", "backend", "java", "quarkus", maven=("quarkus-resteasy", "quarkus-rest", "quarkus-core")),
    _t("micronaut", "Micronaut", "backend", "java", "micronaut", maven=("micronaut-http-server-netty", "micronaut-core")),
    _t("aspnet-core", "ASP.NET Core", "backend", "csharp", "dotnet", nuget=("microsoft.aspnetcore.app", "microsoft.aspnetcore.mvc")),
    _t("laravel", "Laravel", "backend", "php", "laravel", composer=("laravel/framework",)),
    _t("symfony", "Symfony", "backend", "php", "symfony", composer=("symfony/framework-bundle",)),
    _t("rails", "Ruby on Rails", "backend", "ruby", "rubyonrails", gem=("rails",)),
    _t("gin", "Gin", "backend", "go", "gin", go=("github.com/gin-gonic/gin",)),
    _t("echo", "Echo", "backend", "go", "go", go=("github.com/labstack/echo",)),
    _t("fiber", "Fiber", "backend", "go", "go", go=("github.com/gofiber/fiber",)),
    _t("actix", "Actix Web", "backend", "rust", "rust", cargo=("actix-web",)),
    _t("axum", "Axum", "backend", "rust", "rust", cargo=("axum",)),
    # Frontend
    _t("react", "React", "frontend", "javascript", "react", npm=("react",)),
    _t("vue", "Vue", "frontend", "javascript", "vuedotjs", npm=("vue",)),
    _t("angular", "Angular", "frontend", "typescript", "angular", npm=("@angular/core",)),
    _t("svelte", "Svelte", "frontend", "javascript", "svelte", npm=("svelte",)),
    _t("nextjs", "Next.js", "frontend", "javascript", "nextdotjs", npm=("next",)),
    _t("nuxt", "Nuxt", "frontend", "javascript", "nuxt", npm=("nuxt",)),
    _t("solidjs", "SolidJS", "frontend", "javascript", "solid", npm=("solid-js",)),
    _t("jquery", "jQuery", "frontend", "javascript", "jquery", npm=("jquery",)),
    _t("htmx", "htmx", "frontend", "javascript", "htmx", npm=("htmx.org",)),
    # Data
    _t("sqlite", "SQLite", "database", None, "sqlite"),
    _t("postgresql", "PostgreSQL", "database", None, "postgresql",
       pip=("psycopg2", "psycopg2-binary", "psycopg", "asyncpg"), npm=("pg", "postgres"),
       maven=("postgresql",), go=("github.com/lib/pq", "github.com/jackc/pgx"), images=("postgres",)),
    _t("mysql", "MySQL", "database", None, "mysql",
       pip=("mysqlclient", "pymysql", "mysql-connector-python"), npm=("mysql", "mysql2"),
       maven=("mysql-connector-java", "mysql-connector-j"), go=("github.com/go-sql-driver/mysql",), images=("mysql",)),
    _t("mariadb", "MariaDB", "database", None, "mariadb", images=("mariadb",)),
    _t("mongodb", "MongoDB", "database", None, "mongodb",
       pip=("pymongo", "motor"), npm=("mongodb", "mongoose"), maven=("mongodb-driver-sync",), images=("mongo",)),
    _t("redis", "Redis", "database", None, "redis", pip=("redis",), npm=("redis", "ioredis"), images=("redis",)),
    _t("sqlserver", "SQL Server", "database", None, "microsoftsqlserver", pip=("pyodbc", "pymssql"), npm=("mssql", "tedious"), images=("mssql",)),
    # ORM
    _t("sqlalchemy", "SQLAlchemy", "orm", "python", "sqlalchemy", pip=("sqlalchemy",)),
    _t("sequelize", "Sequelize", "orm", "javascript", "sequelize", npm=("sequelize",)),
    _t("typeorm", "TypeORM", "orm", "typescript", "typeorm", npm=("typeorm",)),
    _t("prisma", "Prisma", "orm", "typescript", "prisma", npm=("prisma", "@prisma/client")),
    _t("mongoose", "Mongoose", "orm", "javascript", "mongoose", npm=("mongoose",)),
    _t("hibernate", "Hibernate", "orm", "java", "hibernate", maven=("hibernate-core", "spring-boot-starter-data-jpa")),
    # Infraestructura
    _t("docker", "Docker", "infra", None, "docker"),
    _t("docker-compose", "Docker Compose", "infra", None, "docker"),
    _t("kubernetes", "Kubernetes", "infra", None, "kubernetes"),
    _t("github-actions", "GitHub Actions", "infra", None, "githubactions"),
    _t("terraform", "Terraform", "infra", None, "terraform"),
    # Testing and build
    _t("pytest", "pytest", "testing", "python", "pytest", pip=("pytest",)),
    _t("jest", "Jest", "testing", "javascript", "jest", npm=("jest",)),
    _t("vitest", "Vitest", "testing", "javascript", "vitest", npm=("vitest",)),
    _t("junit", "JUnit", "testing", "java", "junit5", maven=("junit-jupiter", "junit")),
    _t("maven", "Maven", "build", "java", "apachemaven"),
    _t("gradle", "Gradle", "build", "java", "gradle"),
    _t("npm", "npm", "build", "javascript", "npm"),
    _t("vite", "Vite", "build", "javascript", "vite", npm=("vite",)),
    _t("webpack", "webpack", "build", "javascript", "webpack", npm=("webpack",)),
)

BY_ID: dict[str, Tech] = {tech.id: tech for tech in TECHS}

# Languages are recognized by extension (language -> extensions).
LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "typescript": (".ts", ".tsx"),
    "java": (".java",),
    "kotlin": (".kt", ".kts"),
    "csharp": (".cs",),
    "go": (".go",),
    "php": (".php",),
    "ruby": (".rb",),
    "rust": (".rs",),
}

# Kinds between which proposing a migration makes sense.
MIGRATABLE_KINDS = ("backend", "frontend", "database", "orm", "testing", "build")


def targets_for(tech_id: str) -> list[Tech]:
    """Possible targets: technologies of the same kind. Same-language ones first."""
    source = BY_ID.get(tech_id)
    if source is None or source.kind not in MIGRATABLE_KINDS:
        return []
    others = [tech for tech in TECHS if tech.kind == source.kind and tech.id != source.id]
    return sorted(others, key=lambda tech: (tech.language != source.language, tech.name.lower()))
