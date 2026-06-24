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
    }
  | {
      status: "unsupported";
    };

const unsupportedState: ActiveProblemState = { status: "unsupported" };

function canReadActiveTab() {
  return typeof chrome !== "undefined" && Boolean(chrome.tabs?.query);
}

async function getActiveProblemState(): Promise<ActiveProblemState> {
  if (!canReadActiveTab()) {
    return unsupportedState;
  }

  const [activeTab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  const match = parseLeetCodeProblemUrl(activeTab?.url);

  if (!match.isSupported) {
    return unsupportedState;
  }

  return {
    status: "detected",
    slug: match.slug,
    title: getProblemDisplayTitle(match.slug, activeTab?.title),
    url: match.url
  };
}

export function useActiveProblem() {
  const [activeProblem, setActiveProblem] = useState<ActiveProblemState>({
    status: "checking"
  });

  useEffect(() => {
    let isMounted = true;

    const refreshActiveProblem = async () => {
      try {
        const nextState = await getActiveProblemState();

        if (isMounted) {
          setActiveProblem(nextState);
        }
      } catch {
        if (isMounted) {
          setActiveProblem(unsupportedState);
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
      _tabId: number,
      changeInfo: chrome.tabs.TabChangeInfo
    ) => {
      if (changeInfo.url || changeInfo.status === "complete") {
        void refreshActiveProblem();
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
