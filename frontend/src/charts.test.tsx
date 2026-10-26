import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { FoldBars, HBar, LineChart } from "./components/charts";

afterEach(cleanup);

describe("charts", () => {
  it("shows empty states instead of fake data", () => {
    render(<LineChart xs={[]} series={[]} xLabel="K" yLabel="y" />);
    expect(screen.getByRole("status").textContent).toMatch(/No results/);
  });
  it("marks a model that did not run, with an accessible table", () => {
    render(<LineChart xs={[3, 5]} xLabel="K" yLabel="Coverage" series={[{ name: "tabpfn", values: [null, null] }, { name: "naive_frequency", values: [0.2, 0.4] }]} />);
    expect(screen.getByText(/TabPFN — not run/)).toBeTruthy();
    expect(screen.getByText("View as table")).toBeTruthy();
    expect(screen.getAllByText("not run").length).toBe(2);
  });
  it("handles single-year fold data and all-zero bars", () => {
    render(<><FoldBars years={[2024]} xLabel="Year" yLabel="Coverage" series={[{ name: "random", values: [0.3] }]} /><HBar items={[{ label: "a", value: 0 }]} unit="m" /></>);
    expect(screen.getByRole("img").getAttribute("aria-label")).toMatch(/per Year/);
    expect(screen.getByText("Nothing to show yet.")).toBeTruthy();
  });
});
