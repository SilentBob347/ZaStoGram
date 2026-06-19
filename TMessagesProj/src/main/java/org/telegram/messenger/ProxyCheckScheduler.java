/*
 * This is the source code of Telegram for Android v. 5.x.x.
 * It is licensed under GNU GPL v. 2 or later.
 * You should have received a copy of the license in this archive (see LICENSE).
 */

package org.telegram.messenger;

import android.os.SystemClock;

import org.telegram.tgnet.ConnectionsManager;

import java.util.ArrayList;
import java.util.List;

public class ProxyCheckScheduler {

    private static final long PROXY_CHECK_STALE_MS = 2 * 60 * 1000L;
    private static final long PROXY_CHECK_SPACING_MS = 700L;

    private static final ArrayList<Request> queue = new ArrayList<>();
    private static final Runnable startNextRunnable = ProxyCheckScheduler::startNext;
    private static Request activeRequest;

    public interface Callback {
        void onProxyChecked(SharedConfig.ProxyInfo proxyInfo, long time);
        void onProxyCheckQueueFinished();
    }

    public static int enqueueStale(int currentAccount, List<SharedConfig.ProxyInfo> proxyList, Object owner, Callback callback) {
        int added = 0;
        for (int i = 0, count = proxyList.size(); i < count; i++) {
            SharedConfig.ProxyInfo proxyInfo = proxyList.get(i);
            if (!shouldCheck(proxyInfo) || hasPending(proxyInfo)) {
                continue;
            }
            queue.add(new Request(currentAccount, proxyInfo, owner, callback));
            added++;
        }
        if (added > 0) {
            AndroidUtilities.runOnUIThread(startNextRunnable);
        }
        return added;
    }

    public static void cancelOwner(Object owner) {
        if (owner == null) {
            return;
        }
        for (int i = queue.size() - 1; i >= 0; i--) {
            Request request = queue.get(i);
            if (request.owner == owner) {
                request.cancelled = true;
                queue.remove(i);
            }
        }
        if (activeRequest != null && activeRequest.owner == owner) {
            activeRequest.cancelled = true;
            activeRequest.callback = null;
        }
    }

    public static boolean hasOwnerPending(Object owner) {
        if (owner == null) {
            return false;
        }
        if (activeRequest != null && activeRequest.owner == owner && !activeRequest.cancelled) {
            return true;
        }
        for (int i = 0, count = queue.size(); i < count; i++) {
            Request request = queue.get(i);
            if (request.owner == owner && !request.cancelled) {
                return true;
            }
        }
        return false;
    }

    private static boolean shouldCheck(SharedConfig.ProxyInfo proxyInfo) {
        return proxyInfo != null
                && !proxyInfo.checking
                && SystemClock.elapsedRealtime() - proxyInfo.availableCheckTime >= PROXY_CHECK_STALE_MS;
    }

    private static boolean hasPending(SharedConfig.ProxyInfo proxyInfo) {
        if (activeRequest != null && activeRequest.proxyInfo == proxyInfo && !activeRequest.cancelled) {
            return true;
        }
        for (int i = 0, count = queue.size(); i < count; i++) {
            Request request = queue.get(i);
            if (request.proxyInfo == proxyInfo && !request.cancelled) {
                return true;
            }
        }
        return false;
    }

    private static void startNext() {
        if (activeRequest != null) {
            return;
        }
        while (!queue.isEmpty()) {
            Request request = queue.remove(0);
            if (request.cancelled) {
                continue;
            }
            if (!shouldCheck(request.proxyInfo)) {
                notifyOwnerFinishedIfDrained(request);
                continue;
            }
            startRequest(request);
            return;
        }
    }

    private static void startRequest(Request request) {
        activeRequest = request;
        SharedConfig.ProxyInfo proxyInfo = request.proxyInfo;
        proxyInfo.checking = true;
        proxyInfo.proxyCheckPingId = ConnectionsManager.getInstance(request.currentAccount).checkProxy(proxyInfo.address, proxyInfo.port, proxyInfo.username, proxyInfo.password, proxyInfo.secret, time -> AndroidUtilities.runOnUIThread(() -> finishRequest(request, time)));
    }

    private static void finishRequest(Request request, long time) {
        if (activeRequest != request) {
            return;
        }
        SharedConfig.ProxyInfo proxyInfo = request.proxyInfo;
        proxyInfo.availableCheckTime = SystemClock.elapsedRealtime();
        proxyInfo.checking = false;
        if (time == -1) {
            proxyInfo.available = false;
            proxyInfo.ping = 0;
        } else {
            proxyInfo.ping = time;
            proxyInfo.available = true;
        }
        NotificationCenter.getGlobalInstance().postNotificationName(NotificationCenter.proxyCheckDone, proxyInfo);
        if (!request.cancelled && request.callback != null) {
            request.callback.onProxyChecked(proxyInfo, time);
        }
        activeRequest = null;
        notifyOwnerFinishedIfDrained(request);
        AndroidUtilities.runOnUIThread(startNextRunnable, PROXY_CHECK_SPACING_MS);
    }

    private static void notifyOwnerFinishedIfDrained(Request request) {
        if (!request.cancelled && request.callback != null && !hasOwnerPending(request.owner)) {
            request.callback.onProxyCheckQueueFinished();
        }
    }

    private static class Request {
        final int currentAccount;
        final SharedConfig.ProxyInfo proxyInfo;
        final Object owner;
        Callback callback;
        boolean cancelled;

        Request(int currentAccount, SharedConfig.ProxyInfo proxyInfo, Object owner, Callback callback) {
            this.currentAccount = currentAccount;
            this.proxyInfo = proxyInfo;
            this.owner = owner;
            this.callback = callback;
        }
    }
}
