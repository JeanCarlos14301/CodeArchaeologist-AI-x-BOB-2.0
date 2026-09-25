import type { Job } from "../types";

const STATUS_STYLE: Record<Job["status"], string> = {
  queued: "text-stone-500",
  running: "text-amber-700",
  done: "text-emerald-700",
  failed: "text-rose-700",
};

interface Props {
  jobs: Job[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function JobHistory({ jobs, selectedId, onSelect }: Props) {
  if (jobs.length === 0) return <p className="text-sm text-stone-500">Aún no hay auditorías.</p>;
  return (
    <ul className="space-y-1">
      {jobs.map((job) => (
        <li key={job.id}>
          <button
            type="button"
            onClick={() => onSelect(job.id)}
            className={`w-full rounded-md px-2 py-1.5 text-left text-xs hover:bg-stone-100 ${selectedId === job.id ? "bg-stone-200" : ""}`}
          >
            <span className="font-mono">{job.id}</span>{" "}
            <span className="uppercase text-stone-500">{job.execution_mode}</span>{" "}
            <span className={STATUS_STYLE[job.status]}>{job.status}</span>
            <span className="block text-stone-500">{new Date(job.created_at).toLocaleString()}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
