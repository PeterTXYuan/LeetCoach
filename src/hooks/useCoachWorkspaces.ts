import { useCallback, useEffect, useState } from "react";
import {
  emptyWorkspace, loadWorkspaces, saveWorkspaces,
  type CoachWorkspace, type CoachWorkspaces, type SavedHints
} from "../coachWorkspaceStorage";

type WorkspaceState = { ready: boolean; canPersist: boolean; workspaces: CoachWorkspaces };

export function useCoachWorkspaces() {
  const [state, setState] = useState<WorkspaceState>({
    ready: false, canPersist: false, workspaces: {}
  });

  useEffect(() => {
    let mounted = true;
    void loadWorkspaces().catch(() => ({ workspaces: {}, canPersist: false })).then((loaded) => {
      if (mounted) setState({ ready: true, ...loaded });
    });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (state.ready && state.canPersist) saveWorkspaces(state.workspaces);
  }, [state]);

  const updateWorkspace = useCallback((slug: string, update: (current: CoachWorkspace) => CoachWorkspace) => {
    setState((current) => {
      if (!current.ready) return current;
      const before = current.workspaces[slug] ?? emptyWorkspace();
      const after = update(before);
      if (after === before) return current;
      return { ...current, workspaces: { ...current.workspaces, [slug]: after } };
    });
  }, []);

  const updateHints = useCallback((
    slug: string,
    approachId: string,
    update: (current: SavedHints | undefined) => SavedHints | undefined
  ) => {
    updateWorkspace(slug, (workspace) => {
      const before = workspace.hintsByApproach[approachId];
      const after = update(before);
      if (!after || after === before) return workspace;
      return {
        ...workspace,
        hintsByApproach: { ...workspace.hintsByApproach, [approachId]: after }
      };
    });
  }, [updateWorkspace]);

  const workspaceFor = (slug?: string): CoachWorkspace | null =>
    state.ready && slug ? state.workspaces[slug] ?? emptyWorkspace() : null;

  return { ready: state.ready, workspaceFor, updateWorkspace, updateHints };
}
