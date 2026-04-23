export class ApiError extends Error {
  readonly status: number;
  readonly type: string;
  readonly title: string;
  readonly detail: string;

  constructor(status: number, type: string, title: string, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.type = type;
    this.title = title;
    this.detail = detail;
  }
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}
