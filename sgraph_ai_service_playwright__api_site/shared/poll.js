// ── poll.js — adaptive health-poll loop with back-off ───────────────────── //
// Phase 1: first 10 polls every 3s                                           //
// Phase 2: next 10 polls every 5s                                            //
// Phase 3: every 10s thereafter                                              //
// Pauses when the document is hidden. Returns a stop() function.             //

export function startPoll(fetchFn, onResult, options = {}) {
    const { timeout, stopOn = [] } = options;
    const startTime = Date.now();
    let stopped     = false;
    let attempt     = 0;
    let timerId     = null;

    function intervalFor(n) {
        if (n < 10)  return 3000;
        if (n < 20)  return 5000;
        return 10000;
    }

    function stop() {
        stopped = true;
        if (timerId !== null) {
            clearTimeout(timerId);
            timerId = null;
        }
    }

    async function tick() {
        if (stopped) return;

        if (timeout && (Date.now() - startTime) >= timeout) {
            onResult({ status: 'timeout', data: null, error: null });
            stop();
            return;
        }

        if (document.hidden) {
            timerId = setTimeout(tick, intervalFor(attempt));
            return;
        }

        let data  = null;
        let error = null;
        let status;
        try {
            data   = await fetchFn();
            status = data?.status ?? 'ok';
        } catch (err) {
            error  = err;
            status = 'error';
        }

        onResult({ status, data, error });
        attempt += 1;

        if (stopOn.includes(status)) {
            stop();
            return;
        }

        if (!stopped) {
            timerId = setTimeout(tick, intervalFor(attempt));
        }
    }

    function onVisibility() {
        if (!document.hidden && !stopped && timerId === null) {
            tick();
        }
    }

    document.addEventListener('visibilitychange', onVisibility);

    const originalStop = stop;
    function stopAndClean() {
        document.removeEventListener('visibilitychange', onVisibility);
        originalStop();
    }

    tick();
    return stopAndClean;
}
