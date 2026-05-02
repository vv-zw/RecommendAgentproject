Page({
  data: {
    currentShow: null,
    searchName: '',
    searchResult: null,
    searchHistory: [],
    loading: false,
    detailLoading: false,
    errorMsg: '',
    showList: [],
    selectedElements: [],
    rowCount: 0
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === 'function'
      ? app.getBackendUrl()
      : 'http://localhost:5000';
  },

  buildFallbackShow(name) {
    const title = String(name || '').trim() || '未命名剧集';
    return {
      id: `custom_series_${Date.now()}`,
      name: title,
      title,
      coverUrl: '',
      cover_url: '',
      rating: '暂无评分',
      genres: '未知',
      year: '',
      director: '',
      actors: [],
      episodes: '未知',
      region: '未知',
      type: 'series',
      content_type: 'series',
      comment: '暂无短评',
      selectedElements: ['未知']
    };
  },

  normalizeShowItem(item = {}) {
    return {
      id: item.id || `custom_series_${Date.now()}`,
      name: item.name || item.title || '未命名剧集',
      title: item.title || item.name || '未命名剧集',
      coverUrl: item.coverUrl || item.cover_url || item.image || '',
      cover_url: item.cover_url || item.coverUrl || item.image || '',
      rating: item.rating || item.rate || '暂无评分',
      genres: item.genres || item.type || '未知',
      year: item.year || item.release_date || '',
      director: item.director || '',
      actors: item.actors || [],
      episodes: item.episodes || '未知',
      region: item.region || '未知',
      type: item.type || 'series',
      content_type: item.content_type || 'series',
      comment: item.comment || '暂无短评'
    };
  },

  updateRowCount() {
    this.setData({
      rowCount: Math.ceil((this.data.showList.length || 0) / 2)
    });
  },

  applySelectionState(showList, selectedElements = this.data.selectedElements) {
    const selectedSet = new Set(selectedElements || []);
    return (showList || []).map((item) => {
      const selectionKey = item.id || item.name || item.title;
      return {
        ...item,
        checked: selectedSet.has(selectionKey)
      };
    });
  },

  findExistingShowItem(targetItem, requestedName = '') {
    const targetKey = String(targetItem?.id || targetItem?.name || targetItem?.title || '');
    const targetName = String(targetItem?.name || targetItem?.title || requestedName || '').trim();
    return (this.data.showList || []).find((item) => {
      const itemKey = String(item.id || item.name || item.title || '');
      const itemName = String(item.name || item.title || '').trim();
      return itemKey === targetKey || (targetName && itemName === targetName);
    }) || null;
  },

  onSearchInput(e) {
    this.setData({ searchName: e.detail.value });
  },

  appendSearchHistory(name) {
    const title = String(name || '').trim();
    if (!title) {
      return;
    }

    const searchHistory = this.data.searchHistory.filter((item) => item !== title);
    searchHistory.unshift(title);
    if (searchHistory.length > 10) {
      searchHistory.length = 10;
    }

    this.setData({ searchHistory });
    wx.setStorageSync('showSearchHistory', searchHistory);
  },

  searchShow() {
    const searchName = String(this.data.searchName || '').trim();
    if (!searchName) {
      wx.showToast({ title: '请输入剧集名称', icon: 'none' });
      return;
    }

    this.setData({
      loading: true,
      errorMsg: '',
      searchResult: null
    });

    wx.request({
      url: `${this.getBackendUrl()}/api/get-drama-by-name`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: { name: searchName },
      success: (res) => {
        this.setData({ loading: false });

        if (res.data && res.data.code === 0 && res.data.data) {
          const showData = this.normalizeShowItem(res.data.data);
          this.setData({
            searchResult: showData,
            currentShow: showData
          });
          this.appendSearchHistory(searchName);
          return;
        }

        const fallbackShow = this.buildFallbackShow(searchName);
        this.setData({
          searchResult: fallbackShow,
          currentShow: fallbackShow,
          errorMsg: '数据库中未找到该剧集，已为你创建默认条目。'
        });
        this.appendSearchHistory(searchName);
        wx.showToast({ title: '已创建默认条目', icon: 'none' });
      },
      fail: () => {
        const fallbackShow = this.buildFallbackShow(searchName);
        this.setData({
          loading: false,
          searchResult: fallbackShow,
          currentShow: fallbackShow,
          errorMsg: '请求失败，已为你创建默认条目。'
        });
        this.appendSearchHistory(searchName);
        wx.showToast({ title: '已创建默认条目', icon: 'none' });
      }
    });
  },

  loadFromLocalCache() {
    let showList = wx.getStorageSync('showList') || [];
    showList = showList
      .filter((item) => item && (item.id || item.title || item.name))
      .map((item) => this.normalizeShowItem(item));
    const selectedElements = this.data.selectedElements.filter((key) => (
      showList.some((item) => (item.id || item.name || item.title) === key)
    ));

    this.setData({
      showList: this.applySelectionState(showList, selectedElements),
      selectedElements,
      searchHistory: wx.getStorageSync('showSearchHistory') || []
    });
    this.updateRowCount();
  },

  batchQueryShowDetails(showNames) {
    if (!showNames || !showNames.length) {
      return;
    }

    this.setData({ detailLoading: true });
    wx.request({
      url: `${this.getBackendUrl()}/api/get-dramas-by-names`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: {
        names: showNames,
        onlyReturnRequested: true
      },
      success: (res) => {
        this.setData({ detailLoading: false });
        if (!(res.data && res.data.code === 0 && Array.isArray(res.data.results))) {
          return;
        }

        const existingShowMap = new Map(
          (this.data.showList || []).map((item) => [String(item.id || item.name || item.title), item])
        );

        const showList = res.data.results.map((entry) => {
          if (entry && entry.data) {
            const normalizedItem = this.normalizeShowItem({
              ...entry.data,
              title: entry.data.title || entry.matched_title,
              name: entry.data.name || entry.matched_title
            });
            const existingItem = existingShowMap.get(String(normalizedItem.id || normalizedItem.name || normalizedItem.title))
              || this.findExistingShowItem(normalizedItem, entry?.name_requested || entry?.matched_title || '');
            return this.normalizeShowItem({
              ...normalizedItem,
              comment: existingItem?.comment || normalizedItem.comment
            });
          }
          const fallbackItem = this.buildFallbackShow(entry?.name_requested || entry?.matched_title || '');
          const existingItem = existingShowMap.get(String(fallbackItem.id || fallbackItem.name || fallbackItem.title))
            || (this.data.showList || []).find((item) => (
              (item.name || item.title) === (entry?.name_requested || entry?.matched_title || '')
            ));
          return this.normalizeShowItem({
            ...fallbackItem,
            comment: existingItem?.comment || fallbackItem.comment
          });
        });

        this.setData({
          showList: this.applySelectionState(showList)
        });
        wx.setStorageSync('showList', showList);
        this.updateRowCount();
      },
      fail: () => {
        this.setData({ detailLoading: false });
        wx.showToast({ title: '批量查询失败', icon: 'none' });
      }
    });
  },

  selectFromHistory(e) {
    const name = e.currentTarget.dataset.name;
    this.setData({ searchName: name }, () => this.searchShow());
  },

  clearHistory() {
    wx.showModal({
      title: '清空确认',
      content: '确定清空全部搜索历史吗？',
      success: (res) => {
        if (!res.confirm) {
          return;
        }
        this.setData({ searchHistory: [] });
        wx.setStorageSync('showSearchHistory', []);
        wx.showToast({ title: '已清空', icon: 'none' });
      }
    });
  },

  batchSearchShows() {
    if (!this.data.searchHistory.length) {
      wx.showToast({ title: '暂无可查询的历史记录', icon: 'none' });
      return;
    }
    this.batchQueryShowDetails(this.data.searchHistory);
  },

  deleteShow(e) {
    const id = e.currentTarget.dataset.id;
    const name = e.currentTarget.dataset.name;
    wx.showModal({
      title: '删除确认',
      content: '确定删除这部剧集吗？',
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        const showList = this.data.showList.filter((item) => item.id !== id && item.name !== name);
        this.setData({
          showList: this.applySelectionState(showList)
        });
        wx.setStorageSync('showList', showList);
        this.updateRowCount();
        wx.showToast({ title: '删除成功', icon: 'none' });
      }
    });
  },

  batchDelete() {
    const { selectedElements, showList } = this.data;
    if (!selectedElements.length) {
      wx.showToast({ title: '请先选择剧集', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '删除确认',
      content: `确定删除已选中的 ${selectedElements.length} 部剧集吗？`,
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        const newShowList = showList.filter((item) => (
          !selectedElements.includes(item.id) && !selectedElements.includes(item.name)
        ));
        this.setData({
          showList: this.applySelectionState(newShowList, []),
          selectedElements: []
        });
        wx.setStorageSync('showList', newShowList);
        this.updateRowCount();
        wx.showToast({ title: '删除成功', icon: 'none' });
      }
    });
  },

  checkboxChange(e) {
    this.setData({ selectedElements: e.detail.value });
  },

  handleCheckboxTap(e) {
    const value = e.currentTarget.dataset.value;
    const selectedElements = [...this.data.selectedElements];
    const index = selectedElements.indexOf(value);

    if (index > -1) {
      selectedElements.splice(index, 1);
    } else {
      selectedElements.push(value);
    }

    this.setData({
      selectedElements,
      showList: this.applySelectionState(this.data.showList, selectedElements)
    });
  },

  saveToCollection() {
    const { currentShow } = this.data;
    if (!currentShow) {
      wx.showToast({ title: '请先搜索剧集', icon: 'none' });
      return;
    }

    const showToSave = this.normalizeShowItem(currentShow);
    const showList = [...this.data.showList];
    const exists = showList.some((item) => item.id === showToSave.id || item.title === showToSave.title);

    if (exists) {
      wx.showToast({ title: '该剧集已收藏', icon: 'none' });
      return;
    }

    showList.unshift(showToSave);
    this.setData({
      showList: this.applySelectionState(showList)
    });
    this.updateRowCount();
    wx.setStorageSync('showList', showList);
    wx.showToast({ title: '收藏成功', icon: 'success' });
  },

  onPullDownRefresh() {
    const showNames = this.data.showList.map((item) => item.name || item.title).filter(Boolean);
    if (showNames.length) {
      this.batchQueryShowDetails(showNames);
    }
    wx.stopPullDownRefresh();
  },

  onLoad(options) {
    if (options.name) {
      this.setData({ searchName: options.name }, () => this.searchShow());
    }

    this.loadFromLocalCache();

    const showNames = this.data.showList.map((item) => item.name || item.title).filter(Boolean);
    if (showNames.length) {
      setTimeout(() => this.batchQueryShowDetails(showNames), 300);
    }
  },

  onShow() {
    const hasDataChanged = wx.getStorageSync('showDataChanged') || false;
    if (hasDataChanged) {
      this.loadFromLocalCache();
      wx.removeStorageSync('showDataChanged');
    }
  }
});
