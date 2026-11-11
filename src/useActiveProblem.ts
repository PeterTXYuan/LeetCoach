import { useEffect, useState } from "react";
import { getProblemDisplayTitle, parseLeetCodeProblemUrl } from "./problemUrl";

export type ActiveProblemState =
  | {
      status: "checking";
    }
  | {
      status: "detected";
      slug: string;
      title: string;
      url: string;
      tabId?: number;
      navigationRevision: number;
    }
  | {
      status: "unsupported";
      tabId?: number;
      navigationRevision: number;
    };

type TabProblemState =
  | { status: "detected"; slug: string; title: string; url: string; tabId?: number }
  | { status: "unsupported"; tabId?: number };

function canReadActiveTab() {
  return typeof chrome !== "undefined" && Boolean(chrome.tabs?.query);
}

function problemStateForUrl(rawUrl?: string, title?: string, tabId?: number): TabProblemState {
  const match = parseLeetCodeProblemUrl(rawUrl);

  if (!match.isSupported) {
    return { status: "unsupported", tabId };
  }

  return {
    status: "detected",
    slug: match.slug,
    title: getProblemDisplayTitle(match.slug, title),
    url: match.url,
    tabId
  };
}

async function getActiveProblemState(): Promise<TabProblemState> {
  if (!canReadActiveTab()) {
    return { status: "unsupported" };
  }

  const [activeTab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  return problemStateForUrl(activeTab?.url, activeTab?.title, activeTab?.id);
}

export function useActiveProblem() {
  const [activeProblem, setActiveProblem] = useState<ActiveProblemState>({
    status: "checking"
  });

  useEffect(() => {
    let isMounted = true;
    let latestRequest = 0;
    let navigationRevision = 0;
    let activeTabId: number | undefined;

    const refreshActiveProblem = async () => {
      const request = ++latestRequest;
      try {
        const nextState = await getActiveProblemState();

        if (isMounted && request === latestRequest) {
          activeTabId = nextState.tabId;
          setActiveProblem({ ...nextState, navigationRevision });
        }
      } catch {
        if (isMounted && request === latestRequest) {
          activeTabId = undefined;
          setActiveProblem({ status: "unsupported", navigationRevision });
        }
      }
    };

    void refreshActiveProblem();

    if (!canReadActiveTab()) {
      return () => {
        isMounted = false;
      };
    }

    const handleTabActivated = () => {
      void refreshActiveProblem();
    };

    const handleTabUpdated = (
      tabId: number,
      changeInfo: chrome.tabs.TabChangeInfo,
      tab: chrome.tabs.Tab
    ) => {
      if (tabId !== activeTabId) return;

      if (changeInfo.url || changeInfo.status === "complete") {
        navigationRevision += 1;
        if (changeInfo.url || tab?.url) {
          // The event URL is newer than a tabs.query result during LeetCode's navigation.
          latestRequest += 1;
          setActiveProblem({
            ...problemStateForUrl(changeInfo.url ?? tab.url, changeInfo.title ?? tab?.title, tabId),
            navigationRevision
          });
        } else {
          void refreshActiveProblem();
        }
      } else if (changeInfo.title) {
        setActiveProblem((current) => current.status === "detected" && current.tabId === tabId
          ? { ...current, title: getProblemDisplayTitle(current.slug, changeInfo.title) }
          : current);
      }
    };

    chrome.tabs.onActivated.addListener(handleTabActivated);
    chrome.tabs.onUpdated.addListener(handleTabUpdated);

    return () => {
      isMounted = false;
      chrome.tabs.onActivated.removeListener(handleTabActivated);
      chrome.tabs.onUpdated.removeListener(handleTabUpdated);
    };
  }, []);

  return activeProblem;
}
