import { Component, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

class Boundary extends Component<{ children: ReactNode }, { e: string }> {
  state = { e: "" };
  static getDerivedStateFromError(e: Error) { return { e: e.message }; }
  render() { return this.state.e ? <main><p className="err" role="alert">Display error: {this.state.e}. Reload the page; if it persists, report this message.</p></main> : this.props.children; }
}
createRoot(document.getElementById("root")!).render(<Boundary><App /></Boundary>);
