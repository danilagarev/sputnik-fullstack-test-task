/**
 * React Query cache keys.
 *
 * In `shared` because both entities and the widgets that refresh them need to
 * name the same cache: slices of the same layer must not import each other.
 */

export const filesKey = ["files"] as const;
export const alertsKey = ["alerts"] as const;
