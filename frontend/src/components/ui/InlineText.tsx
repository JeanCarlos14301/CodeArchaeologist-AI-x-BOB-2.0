const INLINE = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g;

/**
 * Bob's text with its inline formatting: `code` in mono and **emphasis**. React nodes are built
 * (never HTML), so text with tags is shown as is and never interpreted.
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
