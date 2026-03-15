import React, { useEffect, useState } from "react";
import { invoke } from "@forge/bridge";

type RouteKey =
  | "dashboard"
  | "workflow"
  | "graph"
  | "drift"
  | "health";

type RouteState = {
  key: RouteKey;
  id: string | null;
};

type PingResponse = {
  pong: boolean;
};

const DEFAULT_ROUTE = "#/dashboard";

function parseHash(hash: string): RouteState {
  const normalizedHash = hash.trim() === "" ? DEFAULT_ROUTE : hash;
  const [, routeName = "dashboard", routeId] = normalizedHash.replace(/^#\//, "").split("/");

  switch (routeName) {
    case "workflow":
      return { key: "workflow", id: routeId ?? null };
    case "graph":
      return { key: "graph", id: routeId ?? null };
    case "drift":
      return { key: "drift", id: null };
    case "health":
      return { key: "health", id: routeId ?? null };
    case "dashboard":
    default:
      return { key: "dashboard", id: null };
  }
}

function routeTitle(route: RouteState): string {
  switch (route.key) {
    case "workflow":
      return route.id === null ? "Workflow Detail" : `Workflow ${route.id}`;
    case "graph":
      return route.id === null ? "Graph View" : `Graph ${route.id}`;
    case "drift":
      return "Drift Comparison";
    case "health":
      return route.id === null ? "Health Report" : `Health ${route.id}`;
    case "dashboard":
    default:
      return "Dashboard";
  }
}

function routeDescription(route: RouteState): string {
  switch (route.key) {
    case "workflow":
      return "Detailed workflow metrics and technical debt will render here.";
    case "graph":
      return "This page will host the D3 workflow graph visualization.";
    case "drift":
      return "This page will compare two workflows side by side.";
    case "health":
      return "This page will present health score details and debt items.";
    case "dashboard":
    default:
      return "This page will summarize workflow health across the Jira instance.";
  }
}

function App(): JSX.Element {
  const [route, setRoute] = useState<RouteState>(() => parseHash(window.location.hash));
  const [pingStatus, setPingStatus] = useState<string>("Checking backend connection...");

  useEffect(() => {
    if (window.location.hash.trim() === "") {
      window.location.hash = DEFAULT_ROUTE;
    }

    const onHashChange = (): void => {
      setRoute(parseHash(window.location.hash));
    };

    window.addEventListener("hashchange", onHashChange);

    return () => {
      window.removeEventListener("hashchange", onHashChange);
    };
  }, []);

  useEffect(() => {
    let active = true;

    invoke<PingResponse>("ping", {})
      .then((response) => {
        if (!active) {
          return;
        }

        setPingStatus(response.pong ? "Resolver ping succeeded." : "Resolver ping returned an unexpected payload.");
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        setPingStatus(
          error instanceof Error ? `Resolver ping failed: ${error.message}` : "Resolver ping failed.",
        );
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Workflow Analyzer</p>
        <h1>{routeTitle(route)}</h1>
        <p className="subtitle">{routeDescription(route)}</p>
      </header>

      <nav className="nav-grid" aria-label="Primary">
        <a href="#/dashboard">Dashboard</a>
        <a href="#/workflow/sample-workflow">Workflow Detail</a>
        <a href="#/graph/sample-workflow">Graph View</a>
        <a href="#/drift">Drift Comparison</a>
        <a href="#/health/sample-workflow">Health Report</a>
      </nav>

      <section className="panel">
        <h2>Scaffold Status</h2>
        <p>{pingStatus}</p>
      </section>

      <section className="panel">
        <h2>Next Implementation Slice</h2>
        <p>
          Route skeletons are active. The next milestones will connect Jira workflow data, normalize it into typed
          models, and render analysis output here.
        </p>
      </section>
    </main>
  );
}

export default App;
