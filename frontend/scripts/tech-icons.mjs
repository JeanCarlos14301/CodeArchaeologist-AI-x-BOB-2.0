// Genera src/lib/techIconPaths.ts con SOLO el trazado SVG de cada icono (simple-icons, CC0).
// Importar los objetos completos de simple-icons añade al bundle su `svg` duplicado y metadatos.
// Uso: npm run icons  (tras cambiar la lista o actualizar simple-icons)
import { writeFileSync } from "node:fs";
import * as icons from "simple-icons";

const SLUGS = [
  "angular", "apachemaven", "django", "docker", "dotnet", "express", "fastapi", "fastify", "flask", "gin",
  "githubactions", "go", "gradle", "hibernate", "htmx", "javascript", "jest", "jquery", "junit5", "kotlin", "koa",
  "kubernetes", "laravel", "mariadb", "mongodb", "mongoose", "mysql", "nestjs", "nextdotjs", "npm", "nuxt", "openjdk",
  "php", "postgresql", "prisma", "pytest", "python", "quarkus", "react", "redis", "rubyonrails", "ruby", "rust",
  "sequelize", "solid", "springboot", "sqlalchemy", "sqlite", "svelte", "symfony", "terraform", "typeorm", "typescript",
  "vite", "vitest", "vuedotjs", "webpack",
];

const bySlug = new Map(Object.values(icons).filter((icon) => icon && icon.slug).map((icon) => [icon.slug, icon.path]));
const missing = SLUGS.filter((slug) => !bySlug.has(slug));
if (missing.length) {
  console.error(`Iconos inexistentes en simple-icons: ${missing.join(", ")}`);
  process.exit(1);
}
const body = SLUGS.map((slug) => `  ${JSON.stringify(slug)}: ${JSON.stringify(bySlug.get(slug))},`).join("\n");
writeFileSync(
  new URL("../src/lib/techIconPaths.ts", import.meta.url),
  `// Generado por scripts/tech-icons.mjs a partir de simple-icons (CC0). No editar a mano.\n` +
    `/** Trazado SVG (viewBox 0 0 24 24) de cada tecnología, por slug. */\n` +
    `export const TECH_ICONS: Record<string, string> = {\n${body}\n};\n`,
);
console.log(`techIconPaths.ts: ${SLUGS.length} iconos`);
