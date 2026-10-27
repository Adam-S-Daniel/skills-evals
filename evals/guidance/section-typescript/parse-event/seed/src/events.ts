export interface Event {
  id: string;
  kind: "created" | "deleted";
  at: number;
}

export function describe(event: Event): string {
  return `${event.kind} ${event.id} at ${event.at}`;
}
