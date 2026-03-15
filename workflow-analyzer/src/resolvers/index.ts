import Resolver from "@forge/resolver";

type PingResponse = {
  pong: boolean;
};

const resolver = new Resolver();

resolver.define("ping", async (): Promise<PingResponse> => {
  return { pong: true };
});

resolver.define("getHealthDashboard", async (): Promise<Record<string, never>> => {
  return {};
});

resolver.define("listWorkflows", async (): Promise<never[]> => {
  return [];
});

resolver.define(
  "getWorkflowAnalysis",
  async (): Promise<Record<string, never>> => {
    return {};
  },
);

resolver.define("compareWorkflows", async (): Promise<Record<string, never>> => {
  return {};
});

resolver.define(
  "refreshCache",
  async (): Promise<{ success: boolean; workflowsRefreshed: number; refreshedAt: string }> => {
    return {
      success: true,
      workflowsRefreshed: 0,
      refreshedAt: new Date().toISOString(),
    };
  },
);

export const handler = resolver.getDefinitions();
