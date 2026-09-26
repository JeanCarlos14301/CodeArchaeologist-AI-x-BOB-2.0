import {
  siAngular, siApachemaven, siDjango, siDocker, siDotnet, siExpress, siFastapi, siFastify, siFlask, siGin,
  siGithubactions, siGo, siGradle, siHibernate, siHtmx, siJavascript, siJest, siJquery, siJunit5, siKotlin, siKoa,
  siKubernetes, siLaravel, siMariadb, siMongodb, siMongoose, siMysql, siNestjs, siNextdotjs, siNpm, siNuxt, siOpenjdk,
  siPhp, siPostgresql, siPrisma, siPytest, siPython, siQuarkus, siReact, siRedis, siRubyonrails, siRuby, siRust,
  siSequelize, siSolid, siSpringboot, siSqlalchemy, siSqlite, siSvelte, siSymfony, siTerraform, siTypeorm, siTypescript,
  siVite, siVitest, siVuedotjs, siWebpack,
} from "simple-icons";

/** Trazados SVG monocromos (simple-icons, CC0) por slug. Sin icono, `TechIcon` muestra las iniciales. */
export const TECH_ICONS: Record<string, string> = Object.fromEntries(
  [
    siAngular, siApachemaven, siDjango, siDocker, siDotnet, siExpress, siFastapi, siFastify, siFlask, siGin, siGithubactions,
    siGo, siGradle, siHibernate, siHtmx, siJavascript, siJest, siJquery, siJunit5, siKotlin, siKoa, siKubernetes, siLaravel,
    siMariadb, siMongodb, siMongoose, siMysql, siNestjs, siNextdotjs, siNpm, siNuxt, siOpenjdk, siPhp, siPostgresql, siPrisma,
    siPytest, siPython, siQuarkus, siReact, siRedis, siRubyonrails, siRuby, siRust, siSequelize, siSolid, siSpringboot,
    siSqlalchemy, siSqlite, siSvelte, siSymfony, siTerraform, siTypeorm, siTypescript, siVite, siVitest, siVuedotjs, siWebpack,
  ].map((icon) => [icon.slug, icon.path]),
);
