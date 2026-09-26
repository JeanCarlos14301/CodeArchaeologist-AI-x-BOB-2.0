const INLINE = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g;

/**
 * Texto de Bob con su formato en línea: `código` en mono y **énfasis**. Se construyen nodos de React
 * (nunca HTML), así que un texto con etiquetas se muestra tal cual y no se interpreta.
 */
export function InlineText({ text }: { text: string }) {
  return (
    <>
      {text.split(INLINE).map((part, index) => {
        if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) {
          return <code key={index} className="rounded-tick bg-code px-1 font-mono text-caption text-fg">{part.slice(1, -1)}</code>;
        }
        if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) {
          return <strong key={index} className="font-medium text-fg">{part.slice(2, -2)}</strong>;
        }
        return part;
      })}
    </>
  );
}
