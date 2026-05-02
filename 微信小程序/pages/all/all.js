Page({
  data: {
    totalList: [],
    selectedElements: [],
    loading: true,
    rowCount: 0
  },

  onLoad() {
    this.loadTotalData(true);
  },

  onShow() {
    const hasDataChanged = wx.getStorageSync('totalDataChanged') || false;
    if (hasDataChanged) {
      this.loadTotalData(true);
      wx.removeStorageSync('totalDataChanged');
      return;
    }
    this.loadTotalData(false);
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === 'function'
      ? app.getBackendUrl()
      : 'http://localhost:5000';
  },

  buildFallbackItem(name, contentType) {
    const title = String(name || '').trim() || '未命名条目';
    return {
      id: `${contentType}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      title,
      name: title,
      rating: '暂无评分',
      genres: '未知',
      year: '',
      type: contentType,
      content_type: contentType,
      coverUrl: '',
      cover_url: '',
      selectedElements: ['未知'],
      comment: '暂无短评'
    };
  },

  normalizeTotalItem(item = {}, forcedType = '') {
    const contentType = forcedType || item.content_type || item.type || 'movie';
    let selectedElements = item.selectedElements || item.genres || [];

    if (typeof selectedElements === 'string') {
      selectedElements = selectedElements
        .split(/[,/|、，]/)
        .map((value) => value.trim())
        .filter(Boolean);
    }

    if (!Array.isArray(selectedElements)) {
      selectedElements = [];
    }

    const title = item.title || item.name || '未命名条目';
    const rawId = String(item.id || title).trim();

    return {
      ...item,
      id: rawId,
      name: item.name || title,
      title,
      type: contentType,
      content_type: contentType,
      rating: item.rating || item.rate || item.score || '暂无评分',
      genres: item.genres || (selectedElements.length ? selectedElements.join(' / ') : '未知'),
      year: item.year || item.release_date || '',
      coverUrl: item.coverUrl || item.cover_url || item.image || '',
      cover_url: item.cover_url || item.coverUrl || item.image || '',
      selectedElements,
      comment: item.comment || '暂无短评',
      uniqueId: `${contentType}:${rawId}`
    };
  },

  updateRowCount() {
    this.setData({
      rowCount: Math.ceil((this.data.totalList.length || 0) / 2)
    });
  },

  getMovieList() {
    return (wx.getStorageSync('movieList') || []).map((item) => this.normalizeTotalItem(item, 'movie'));
  },

  getShowList() {
    return (wx.getStorageSync('showList') || []).map((item) => this.normalizeTotalItem(item, 'series'));
  },

  updateCombinedStorage(movieList, showList) {
    const totalMovieList = [...movieList, ...showList];
    wx.setStorageSync('movieList', movieList);
    wx.setStorageSync('showList', showList);
    wx.setStorageSync('totalMovieList', totalMovieList);
  },

  applySelectionState(totalList, selectedElements = this.data.selectedElements) {
    const selectedSet = new Set(selectedElements || []);
    return (totalList || []).map((item) => ({
      ...item,
      checked: selectedSet.has(item.uniqueId)
    }));
  },

  findExistingItemByName(list, targetItem, requestedName = '') {
    const targetKey = String(targetItem?.id || targetItem?.title || targetItem?.name || '');
    const targetName = String(targetItem?.name || targetItem?.title || requestedName || '').trim();
    return (list || []).find((item) => {
      const itemKey = String(item.id || item.title || item.name || '');
      const itemName = String(item.name || item.title || '').trim();
      return itemKey === targetKey || (targetName && itemName === targetName);
    }) || null;
  },

  loadTotalData(forceRefresh = false) {
    const movieList = this.getMovieList();
    const showList = this.getShowList();
    const validSelectedElements = this.data.selectedElements.filter((key) => (
      [...movieList, ...showList].some((item) => item.uniqueId === key)
    ));
    const totalList = this.applySelectionState([...movieList, ...showList], validSelectedElements);

    this.setData({
      totalList,
      loading: false,
      selectedElements: validSelectedElements
    });
    this.updateRowCount();

    if (forceRefresh) {
      this.syncMovieDetails(movieList);
      this.syncShowDetails(showList);
    }
  },

  handleSelectionChange(e) {
    const selectedElements = e.detail.value || [];
    this.setData({
      selectedElements,
      totalList: this.applySelectionState(this.data.totalList, selectedElements)
    });
  },

  syncMovieDetails(movieList) {
    const movieNames = (movieList || []).map((item) => item.name || item.title).filter(Boolean);
    if (!movieNames.length) {
      return;
    }

    wx.request({
      url: `${this.getBackendUrl()}/api/get-movies-by-names`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: {
        names: movieNames,
        onlyReturnRequested: true
      },
      success: (res) => {
        if (!(res.data && res.data.code === 0 && Array.isArray(res.data.results))) {
          return;
        }

        const existingMovieMap = new Map(
          (movieList || []).map((item) => [String(item.id || item.title || item.name), item])
        );

        const updatedMovies = res.data.results.map((entry) => {
          if (entry && entry.data) {
            const normalizedItem = this.normalizeTotalItem({
              ...entry.data,
              title: entry.data.title || entry.matched_title,
              name: entry.data.name || entry.matched_title
            }, 'movie');
            const existingItem = existingMovieMap.get(String(normalizedItem.id || normalizedItem.title || normalizedItem.name))
              || this.findExistingItemByName(movieList, normalizedItem, entry?.name_requested || entry?.matched_title || '');
            return this.normalizeTotalItem({
              ...normalizedItem,
              comment: existingItem?.comment || normalizedItem.comment
            }, 'movie');
          }

          const fallbackItem = this.normalizeTotalItem(
            this.buildFallbackItem(entry?.name_requested || entry?.matched_title || '', 'movie'),
            'movie'
          );
          const existingItem = existingMovieMap.get(String(fallbackItem.id || fallbackItem.title || fallbackItem.name))
            || (movieList || []).find((item) => (
              (item.name || item.title) === (entry?.name_requested || entry?.matched_title || '')
            ));
          return this.normalizeTotalItem({
            ...fallbackItem,
            comment: existingItem?.comment || fallbackItem.comment
          }, 'movie');
        });

        this.updateCombinedStorage(updatedMovies, this.getShowList());
        this.loadTotalData(false);
      }
    });
  },

  syncShowDetails(showList) {
    const showNames = (showList || []).map((item) => item.name || item.title).filter(Boolean);
    if (!showNames.length) {
      return;
    }

    wx.request({
      url: `${this.getBackendUrl()}/api/get-dramas-by-names`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: {
        names: showNames,
        onlyReturnRequested: true
      },
      success: (res) => {
        if (!(res.data && res.data.code === 0 && Array.isArray(res.data.results))) {
          return;
        }

        const existingShowMap = new Map(
          (showList || []).map((item) => [String(item.id || item.title || item.name), item])
        );

        const updatedShows = res.data.results.map((entry) => {
          if (entry && entry.data) {
            const normalizedItem = this.normalizeTotalItem({
              ...entry.data,
              title: entry.data.title || entry.matched_title,
              name: entry.data.name || entry.matched_title
            }, 'series');
            const existingItem = existingShowMap.get(String(normalizedItem.id || normalizedItem.title || normalizedItem.name))
              || this.findExistingItemByName(showList, normalizedItem, entry?.name_requested || entry?.matched_title || '');
            return this.normalizeTotalItem({
              ...normalizedItem,
              comment: existingItem?.comment || normalizedItem.comment
            }, 'series');
          }

          const fallbackItem = this.normalizeTotalItem(
            this.buildFallbackItem(entry?.name_requested || entry?.matched_title || '', 'series'),
            'series'
          );
          const existingItem = existingShowMap.get(String(fallbackItem.id || fallbackItem.title || fallbackItem.name))
            || (showList || []).find((item) => (
              (item.name || item.title) === (entry?.name_requested || entry?.matched_title || '')
            ));
          return this.normalizeTotalItem({
            ...fallbackItem,
            comment: existingItem?.comment || fallbackItem.comment
          }, 'series');
        });

        this.updateCombinedStorage(this.getMovieList(), updatedShows);
        this.loadTotalData(false);
      }
    });
  },

  toggleItemSelection(e) {
    const key = e.currentTarget.dataset.key;
    if (!key) {
      return;
    }

    const selectedElements = [...this.data.selectedElements];
    const index = selectedElements.indexOf(key);
    if (index >= 0) {
      selectedElements.splice(index, 1);
    } else {
      selectedElements.push(key);
    }

    this.setData({
      selectedElements,
      totalList: this.applySelectionState(this.data.totalList, selectedElements)
    });
  },

  toggleSelectAll() {
    const { totalList, selectedElements } = this.data;
    if (!totalList.length) {
      return;
    }

    if (selectedElements.length === totalList.length) {
      this.setData({
        selectedElements: [],
        totalList: this.applySelectionState(totalList, [])
      });
      return;
    }

    const nextSelectedElements = totalList.map((item) => item.uniqueId);
    this.setData({
      selectedElements: nextSelectedElements,
      totalList: this.applySelectionState(totalList, nextSelectedElements)
    });
  },

  deleteItem(e) {
    const key = e.currentTarget.dataset.key;
    const item = this.data.totalList.find((entry) => entry.uniqueId === key);
    if (!item) {
      return;
    }

    wx.showModal({
      title: '删除确认',
      content: `确定删除“${item.title || item.name}”吗？`,
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        this.removeItemsByKeys([key]);
        wx.showToast({ title: '删除成功', icon: 'none' });
      }
    });
  },

  batchDelete() {
    const { selectedElements } = this.data;
    if (!selectedElements.length) {
      wx.showToast({ title: '请先选择条目', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '删除确认',
      content: `确定删除已选中的 ${selectedElements.length} 个条目吗？`,
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        this.removeItemsByKeys(selectedElements);
        wx.showToast({ title: '删除成功', icon: 'none' });
      }
    });
  },

  removeItemsByKeys(keys) {
    const keySet = new Set(keys);
    const movieList = this.getMovieList().filter((item) => !keySet.has(item.uniqueId));
    const showList = this.getShowList().filter((item) => !keySet.has(item.uniqueId));
    const alreadyList = (wx.getStorageSync('alreadyList') || []).filter((item) => {
      const normalized = this.normalizeTotalItem(item, item.content_type || item.type || 'movie');
      return !keySet.has(normalized.uniqueId);
    });

    wx.setStorageSync('alreadyList', alreadyList);
    wx.setStorageSync('totalDataChanged', true);
    this.updateCombinedStorage(movieList, showList);
    this.setData({
      selectedElements: [],
      totalList: this.applySelectionState(this.data.totalList, [])
    });
    this.loadTotalData(false);
  },

  clearAllData() {
    wx.showModal({
      title: '清空确认',
      content: '确定清空全部电影、剧集和待看数据吗？',
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        wx.setStorageSync('movieList', []);
        wx.setStorageSync('showList', []);
        wx.setStorageSync('alreadyList', []);
        wx.setStorageSync('totalMovieList', []);
        wx.setStorageSync('totalDataChanged', true);

        this.setData({
          totalList: [],
          selectedElements: []
        });
        this.updateRowCount();
        wx.showToast({ title: '已清空', icon: 'none' });
      }
    });
  }
});
