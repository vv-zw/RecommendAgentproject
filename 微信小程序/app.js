App({
  globalData: {
    backendUrl: 'http://localhost:5000',
    userInfo: null
  },

  onLaunch() {
    this.hydrateUserState().catch((error) => {
      console.error('hydrate_user_state_failed', error);
      this.checkAndSyncData();
    });
  },

  getBackendUrl() {
    return this.globalData.backendUrl || 'http://localhost:5000';
  },

  normalizeContentType(type, fallback = '') {
    const value = String(type || '').trim().toLowerCase();
    const typeMap = {
      movie: 'movie',
      series: 'series',
      show: 'series',
      tv: 'series',
      '电影': 'movie',
      '剧集': 'series',
      '电视剧': 'series'
    };
    return typeMap[value] || fallback || '';
  },

  normalizeGenres(item) {
    const rawGenres = item?.genres ?? item?.selectedElements ?? [];

    if (Array.isArray(rawGenres)) {
      return rawGenres.map((genre) => String(genre).trim()).filter(Boolean);
    }

    if (typeof rawGenres === 'string') {
      return rawGenres
        .split(/[,/|、，]/)
        .map((genre) => genre.trim())
        .filter(Boolean);
    }

    return [];
  },

  buildPreferenceItem(item, fallbackType = '') {
    if (!item || typeof item !== 'object') {
      return null;
    }

    const id = String(item.id || '').trim();
    const title = String(item.title || item.name || '').trim();
    const contentType = this.normalizeContentType(
      item.content_type || item.contentType || item.type,
      fallbackType
    );

    if (!id || !title || !contentType) {
      return null;
    }

    return {
      id,
      title,
      name: title,
      genres: this.normalizeGenres(item),
      selectedElements: this.normalizeGenres(item),
      rating: Number(item.rating || item.score || 0) || 0,
      comment: String(item.comment || '').trim(),
      cover_url: item.cover_url || item.coverUrl || '',
      coverUrl: item.cover_url || item.coverUrl || '',
      year: item.year || '',
      director: item.director || '',
      actors: item.actors || '',
      type: contentType,
      content_type: contentType
    };
  },

  buildWatchlistCacheItem(entry) {
    if (!entry || typeof entry !== 'object') {
      return null;
    }

    const rawItem = entry.data || entry;
    const contentType = this.normalizeContentType(entry.type || rawItem.type || rawItem.content_type, '');
    const normalized = this.buildPreferenceItem(rawItem, contentType);
    if (!normalized) {
      return null;
    }

    return {
      ...normalized,
      added_at: entry.added_at || rawItem.added_at || '',
      addedTime: entry.added_at || rawItem.added_at || Date.now()
    };
  },

  dedupePreferences(list) {
    const uniqueMap = new Map();

    list.forEach((item) => {
      const normalized = this.buildPreferenceItem(item, item?._fallbackType || '');
      if (!normalized) {
        return;
      }

      const key = `${normalized.content_type}:${normalized.id}`;
      if (!uniqueMap.has(key)) {
        uniqueMap.set(key, normalized);
      }
    });

    return Array.from(uniqueMap.values());
  },

  mergeUniqueItems(list) {
    const uniqueMap = new Map();
    (list || []).forEach((item) => {
      const contentType = this.normalizeContentType(item.content_type || item.type, '');
      const id = String(item.id || '').trim();
      if (!contentType || !id) {
        return;
      }
      uniqueMap.set(`${contentType}:${id}`, { ...item, type: contentType, content_type: contentType });
    });
    return Array.from(uniqueMap.values());
  },

  updateTotalListCache() {
    const merged = this.mergeUniqueItems([
      ...(wx.getStorageSync('movieList') || []),
      ...(wx.getStorageSync('showList') || []),
      ...(wx.getStorageSync('alreadyList') || [])
    ]);
    wx.setStorageSync('totalMovieList', merged);
    return merged;
  },

  cachePreferenceLists(preferencesInput) {
    const grouped = Array.isArray(preferencesInput)
      ? {
          movie: preferencesInput.filter((item) => this.normalizeContentType(item.content_type || item.type, '') === 'movie'),
          series: preferencesInput.filter((item) => this.normalizeContentType(item.content_type || item.type, '') === 'series')
        }
      : (preferencesInput || {});

    const movieList = this.dedupePreferences((grouped.movie || []).map((item) => ({ ...item, _fallbackType: 'movie' })));
    const showList = this.dedupePreferences((grouped.series || []).map((item) => ({ ...item, _fallbackType: 'series' })));

    wx.setStorageSync('movieList', movieList);
    wx.setStorageSync('showList', showList);
    wx.setStorageSync('seriesList', showList);
    this.updateTotalListCache();
    return { movie: movieList, series: showList };
  },

  cacheWatchlist(watchlist) {
    const alreadyList = (watchlist || [])
      .map((item) => this.buildWatchlistCacheItem(item))
      .filter(Boolean);

    wx.setStorageSync('alreadyList', alreadyList);
    this.updateTotalListCache();
    return alreadyList;
  },

  collectPreferences() {
    const movieList = wx.getStorageSync('movieList') || [];
    const showList = wx.getStorageSync('showList') || [];
    const legacySeriesList = wx.getStorageSync('seriesList') || [];
    const alreadyList = wx.getStorageSync('alreadyList') || [];

    return this.dedupePreferences([
      ...movieList.map((item) => ({ ...item, _fallbackType: 'movie' })),
      ...showList.map((item) => ({ ...item, _fallbackType: 'series' })),
      ...legacySeriesList.map((item) => ({ ...item, _fallbackType: 'series' })),
      ...alreadyList
    ]);
  },

  fetchUserPreferences(contentType = '') {
    const normalizedType = this.normalizeContentType(contentType, '');
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/user-preferences`,
        data: normalizedType ? { type: normalizedType } : {},
        success: (res) => {
          if (res.data && res.data.code === 0) {
            resolve(res);
            return;
          }
          reject(new Error((res.data && res.data.error) || 'preferences_fetch_failed'));
        },
        fail: reject
      });
    });
  },

  refreshPreferenceCache(contentType = '') {
    return this.fetchUserPreferences(contentType).then((res) => {
      if (contentType) {
        const grouped = {
          movie: wx.getStorageSync('movieList') || [],
          series: wx.getStorageSync('showList') || []
        };
        grouped[this.normalizeContentType(contentType)] = res.data.preferences || [];
        this.cachePreferenceLists(grouped);
      } else {
        this.cachePreferenceLists(res.data.preferences || {});
      }
      return res;
    });
  },

  fetchWatchlist(contentType = '') {
    const normalizedType = this.normalizeContentType(contentType, '');
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/watchlist`,
        data: normalizedType ? { type: normalizedType } : {},
        success: (res) => {
          if (res.data && res.data.code === 0) {
            resolve(res);
            return;
          }
          reject(new Error((res.data && res.data.error) || 'watchlist_fetch_failed'));
        },
        fail: reject
      });
    });
  },

  refreshWatchlistCache(contentType = '') {
    return this.fetchWatchlist(contentType).then((res) => {
      if (contentType) {
        const normalizedType = this.normalizeContentType(contentType, '');
        const currentItems = wx.getStorageSync('alreadyList') || [];
        const retained = currentItems.filter(
          (item) => this.normalizeContentType(item.content_type || item.type, '') !== normalizedType
        );
        const incoming = (res.data.watchlist || [])
          .map((item) => this.buildWatchlistCacheItem(item))
          .filter(Boolean);
        this.cacheWatchlist([...retained, ...incoming]);
      } else {
        this.cacheWatchlist(res.data.watchlist || []);
      }
      return res;
    });
  },

  hydrateUserState() {
    return Promise.all([
      this.refreshPreferenceCache(),
      this.refreshWatchlistCache()
    ]);
  },

  checkAndSyncData() {
    const preferences = this.collectPreferences();
    this.syncUserData({
      preferences,
      silent: true
    }).catch((error) => {
      console.error('startup_sync_failed', error);
    });
  },

  syncUserData(options = {}) {
    const {
      preferences = this.collectPreferences(),
      silent = false,
      onSuccess,
      onFail
    } = options;

    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/sync-user-data`,
        method: 'POST',
        data: { preferences },
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (!(res.data && res.data.code === 0)) {
            const error = new Error((res.data && res.data.error) || 'sync_failed');
            if (!silent) {
              console.error('sync_user_data_failed', error.message);
            }
            if (typeof onFail === 'function') {
              onFail(error);
            }
            reject(error);
            return;
          }

          this.refreshPreferenceCache().catch((error) => {
            console.error('refresh_preference_cache_after_sync_failed', error);
          }).finally(() => {
            if (typeof onSuccess === 'function') {
              onSuccess(res);
            }
            resolve(res);
          });
        },
        fail: (err) => {
          if (!silent) {
            console.error('sync_user_data_request_failed', err);
          }
          if (typeof onFail === 'function') {
            onFail(err);
          }
          reject(err);
        }
      });
    });
  },

  addWatchlistItem(item, options = {}) {
    const {
      onSuccess,
      onFail
    } = options;
    const payloadItem = this.buildPreferenceItem(item, this.normalizeContentType(item?.content_type || item?.type, ''));
    if (!payloadItem) {
      const error = new Error('invalid_watchlist_item');
      if (typeof onFail === 'function') {
        onFail(error);
      }
      return Promise.reject(error);
    }

    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/watchlist/add`,
        method: 'POST',
        data: {
          item_id: payloadItem.id,
          type: payloadItem.content_type,
          data: payloadItem
        },
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (!(res.data && res.data.code === 0)) {
            const error = new Error((res.data && res.data.error) || 'watchlist_add_failed');
            if (typeof onFail === 'function') {
              onFail(error);
            }
            reject(error);
            return;
          }

          this.refreshWatchlistCache(payloadItem.content_type).catch((error) => {
            console.error('refresh_watchlist_cache_after_add_failed', error);
          }).finally(() => {
            if (typeof onSuccess === 'function') {
              onSuccess(res);
            }
            resolve(res);
          });
        },
        fail: (err) => {
          if (typeof onFail === 'function') {
            onFail(err);
          }
          reject(err);
        }
      });
    });
  },

  removeWatchlistItem(itemId, contentType, options = {}) {
    const {
      onSuccess,
      onFail
    } = options;
    const normalizedType = this.normalizeContentType(contentType, '');
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/watchlist/remove`,
        method: 'POST',
        data: {
          item_id: itemId,
          type: normalizedType
        },
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (!(res.data && res.data.code === 0)) {
            const error = new Error((res.data && res.data.error) || 'watchlist_remove_failed');
            if (typeof onFail === 'function') {
              onFail(error);
            }
            reject(error);
            return;
          }

          this.refreshWatchlistCache(normalizedType).catch((error) => {
            console.error('refresh_watchlist_cache_after_remove_failed', error);
          }).finally(() => {
            if (typeof onSuccess === 'function') {
              onSuccess(res);
            }
            resolve(res);
          });
        },
        fail: (err) => {
          if (typeof onFail === 'function') {
            onFail(err);
          }
          reject(err);
        }
      });
    });
  },

  clearWatchlist(contentType = '', options = {}) {
    const {
      onSuccess,
      onFail
    } = options;
    const normalizedType = this.normalizeContentType(contentType, '');
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/watchlist/clear`,
        method: 'POST',
        data: normalizedType ? { type: normalizedType } : {},
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (!(res.data && res.data.code === 0)) {
            const error = new Error((res.data && res.data.error) || 'watchlist_clear_failed');
            if (typeof onFail === 'function') {
              onFail(error);
            }
            reject(error);
            return;
          }

          this.refreshWatchlistCache(normalizedType).catch((error) => {
            console.error('refresh_watchlist_cache_after_clear_failed', error);
          }).finally(() => {
            if (typeof onSuccess === 'function') {
              onSuccess(res);
            }
            resolve(res);
          });
        },
        fail: (err) => {
          if (typeof onFail === 'function') {
            onFail(err);
          }
          reject(err);
        }
      });
    });
  },

  refreshRecommendations(contentType = '', options = {}) {
    const {
      silent = false,
      onSuccess,
      onFail
    } = options;

    const normalizedType = this.normalizeContentType(contentType, '');
    const payload = normalizedType ? { type: normalizedType } : {};

    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.getBackendUrl()}/refresh-recommendations`,
        method: 'POST',
        data: payload,
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.data && res.data.code === 0) {
            if (typeof onSuccess === 'function') {
              onSuccess(res);
            }
            resolve(res);
            return;
          }

          const error = new Error((res.data && res.data.error) || 'refresh_failed');
          if (!silent) {
            console.error('refresh_recommendations_failed', error.message);
          }
          if (typeof onFail === 'function') {
            onFail(error);
          }
          reject(error);
        },
        fail: (err) => {
          if (!silent) {
            console.error('refresh_recommendations_request_failed', err);
          }
          if (typeof onFail === 'function') {
            onFail(err);
          }
          reject(err);
        }
      });
    });
  },

  pollRefreshJob(jobId, options = {}) {
    const {
      interval = 1500,
      timeout = 90000,
      onSuccess,
      onFail
    } = options;

    return new Promise((resolve, reject) => {
      if (!jobId) {
        const error = new Error('missing_job_id');
        if (typeof onFail === 'function') {
          onFail(error);
        }
        reject(error);
        return;
      }

      const startedAt = Date.now();
      const poll = () => {
        wx.request({
          url: `${this.getBackendUrl()}/refresh-status`,
          data: { job_id: jobId },
          success: (res) => {
            if (!res.data || res.data.code !== 0) {
              const error = new Error((res.data && res.data.error) || 'refresh_status_failed');
              if (typeof onFail === 'function') {
                onFail(error);
              }
              reject(error);
              return;
            }

            if (res.data.status === 'done') {
              if (typeof onSuccess === 'function') {
                onSuccess(res);
              }
              resolve(res);
              return;
            }

            if (res.data.status === 'failed') {
              const error = new Error(res.data.error || 'refresh_job_failed');
              if (typeof onFail === 'function') {
                onFail(error);
              }
              reject(error);
              return;
            }

            if (Date.now() - startedAt >= timeout) {
              const error = new Error('refresh_timeout');
              if (typeof onFail === 'function') {
                onFail(error);
              }
              reject(error);
              return;
            }

            setTimeout(poll, interval);
          },
          fail: (err) => {
            if (typeof onFail === 'function') {
              onFail(err);
            }
            reject(err);
          }
        });
      };

      poll();
    });
  },

  syncAndRefresh(contentType = '', options = {}) {
    const {
      silent = false,
      onSuccess,
      onFail
    } = options;
    const normalizedType = this.normalizeContentType(contentType, '');

    return this.syncUserData({
      silent
    }).then((syncRes) => {
      const syncData = syncRes.data || {};
      const jobId = normalizedType && syncData.jobs ? syncData.jobs[normalizedType] : '';

      if (jobId) {
        return this.pollRefreshJob(jobId).then((statusRes) => ({
          syncResult: syncRes,
          refreshResult: statusRes
        }));
      }

      return this.refreshRecommendations(normalizedType, { silent }).then((refreshRes) => {
        const refreshData = refreshRes.data || {};
        if (refreshData.status === 'done' || refreshData.reused) {
          return {
            syncResult: syncRes,
            refreshResult: refreshRes
          };
        }

        if (refreshData.job_id) {
          return this.pollRefreshJob(refreshData.job_id).then((statusRes) => ({
            syncResult: syncRes,
            refreshResult: statusRes
          }));
        }

        return {
          syncResult: syncRes,
          refreshResult: refreshRes
        };
      });
    }).then((result) => {
      if (typeof onSuccess === 'function') {
        onSuccess(result);
      }
      return result;
    }).catch((error) => {
      if (!silent) {
        console.error('sync_and_refresh_failed', error);
      }
      if (typeof onFail === 'function') {
        onFail(error);
      }
      throw error;
    });
  }
});
