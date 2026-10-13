import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main className="boot-state">
          <div className="error-box" role="alert">
            <div>
              <h1>Trang chưa tải được</h1>
              <p>
                Vui lòng tải lại để tiếp tục. Thông tin đã lưu trên máy chủ được
                giữ nguyên.
              </p>
              <button
                className="button primary"
                onClick={() => window.location.reload()}
              >
                Tải lại trang
              </button>
            </div>
          </div>
        </main>
      );
    return this.props.children;
  }
}
