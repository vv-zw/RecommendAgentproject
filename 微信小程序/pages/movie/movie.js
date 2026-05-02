Page({
  data: {
    currentMovie: null,
    searchName: '',
    searchResult: null,
    searchHistory: [],
    loading: false,
    detailLoading: false,
    errorMsg: '',
    movieList: [],
    selectedElements: [],
    rowCount: 0
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === 'function'
      ? app.getBackendUrl()
      : 'http://localhost:5000';
  },

  buildFallbackMovie(name) {
    const title = String(name || '').trim() || '未命名电影';
    return {
      id: `custom_movie_${Date.now()}`,
      name: title,
      title,
      coverUrl: '',
      cover_url: '',
      rating: '暂无评分',
      genres: '未知',
      year: '',
      director: '',
      actors: [],
      duration: '未知',
      country: '未知',
      type: 'movie',
      content_type: 'movie',
      comment: '暂无短评',
      selectedElements: ['未知']
    };
  },

  normalizeMovieItem(item = {}) {
    return {
      id: item.id || `custom_movie_${Date.now()}`,
      name: item.name || item.title || '未命名电影',
      title: item.title || item.name || '未命名电影',
      coverUrl: item.coverUrl || item.cover_url || item.image || '',
      cover_url: item.cover_url || item.coverUrl || item.image || '',
      rating: item.rating || item.rate || '暂无评分',
      genres: item.genres || item.type || '未知',
      year: item.year || item.release_date || '',
      director: item.director || '',
      actors: item.actors || [],
      duration: item.duration || '未知',
      country: item.country || '未知',
      type: item.type || 'movie',
      content_type: item.content_type || 'movie',
      comment: item.comment || '暂无短评'
    };
  },

  updateRowCount() {
    this.setData({
      rowCount: Math.ceil((this.data.movieList.length || 0) / 2)
    });
  },

  applySelectionState(movieList, selectedElements = this.data.selectedElements) {
    const selectedSet = new Set(selectedElements || []);
    return (movieList || []).map((item) => {
      const selectionKey = item.id || item.title || item.name;
      return {
        ...item,
        checked: selectedSet.has(selectionKey)
      };
    });
  },

  findExistingMovieItem(targetItem, requestedName = '') {
    const targetKey = String(targetItem?.id || targetItem?.title || targetItem?.name || '');
    const targetName = String(targetItem?.name || targetItem?.title || requestedName || '').trim();
    return (this.data.movieList || []).find((item) => {
      const itemKey = String(item.id || item.title || item.name || '');
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
    wx.setStorageSync('movieSearchHistory', searchHistory);
  },

  searchMovie() {
    const searchName = String(this.data.searchName || '').trim();
    if (!searchName) {
      wx.showToast({ title: '请输入电影名称', icon: 'none' });
      return;
    }

    this.setData({
      loading: true,
      errorMsg: '',
      searchResult: null
    });

    wx.request({
      url: `${this.getBackendUrl()}/api/get-movie-by-name`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: { name: searchName },
      success: (res) => {
        this.setData({ loading: false });

        if (res.data && res.data.code === 0 && res.data.data) {
          const movieData = this.normalizeMovieItem(res.data.data);
          this.setData({
            searchResult: movieData,
            currentMovie: movieData
          });
          this.appendSearchHistory(searchName);
          return;
        }

        const fallbackMovie = this.buildFallbackMovie(searchName);
        this.setData({
          searchResult: fallbackMovie,
          currentMovie: fallbackMovie,
          errorMsg: '数据库中未找到该电影，已为你创建默认条目。'
        });
        this.appendSearchHistory(searchName);
        wx.showToast({ title: '已创建默认条目', icon: 'none' });
      },
      fail: () => {
        const fallbackMovie = this.buildFallbackMovie(searchName);
        this.setData({
          loading: false,
          searchResult: fallbackMovie,
          currentMovie: fallbackMovie,
          errorMsg: '请求失败，已为你创建默认条目。'
        });
        this.appendSearchHistory(searchName);
        wx.showToast({ title: '已创建默认条目', icon: 'none' });
      }
    });
  },

  loadFromLocalCache() {
    let movieList = wx.getStorageSync('movieList') || [];
    movieList = movieList
      .filter((item) => item && (item.id || item.title || item.name))
      .map((item) => this.normalizeMovieItem(item));
    const selectedElements = this.data.selectedElements.filter((key) => (
      movieList.some((item) => (item.id || item.title || item.name) === key)
    ));

    this.setData({
      movieList: this.applySelectionState(movieList, selectedElements),
      selectedElements,
      searchHistory: wx.getStorageSync('movieSearchHistory') || []
    });
    this.updateRowCount();
  },

  batchQueryMovieDetails(movieNames) {
    if (!movieNames || !movieNames.length) {
      return;
    }

    this.setData({ detailLoading: true });
    wx.request({
      url: `${this.getBackendUrl()}/api/get-movies-by-names`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: {
        names: movieNames,
        onlyReturnRequested: true
      },
      success: (res) => {
        this.setData({ detailLoading: false });
        if (!(res.data && res.data.code === 0 && Array.isArray(res.data.results))) {
          return;
        }

        const existingMovieMap = new Map(
          (this.data.movieList || []).map((item) => [String(item.id || item.title || item.name), item])
        );

        const movieList = res.data.results.map((entry) => {
          if (entry && entry.data) {
            const normalizedItem = this.normalizeMovieItem({
              ...entry.data,
              title: entry.data.title || entry.matched_title,
              name: entry.data.name || entry.matched_title
            });
            const existingItem = existingMovieMap.get(String(normalizedItem.id || normalizedItem.title || normalizedItem.name))
              || this.findExistingMovieItem(normalizedItem, entry?.name_requested || entry?.matched_title || '');
            return this.normalizeMovieItem({
              ...normalizedItem,
              comment: existingItem?.comment || normalizedItem.comment
            });
          }
          const fallbackItem = this.buildFallbackMovie(entry?.name_requested || entry?.matched_title || '');
          const existingItem = existingMovieMap.get(String(fallbackItem.id || fallbackItem.title || fallbackItem.name))
            || (this.data.movieList || []).find((item) => (
              (item.name || item.title) === (entry?.name_requested || entry?.matched_title || '')
            ));
          return this.normalizeMovieItem({
            ...fallbackItem,
            comment: existingItem?.comment || fallbackItem.comment
          });
        });

        this.setData({
          movieList: this.applySelectionState(movieList)
        });
        wx.setStorageSync('movieList', movieList);
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
    this.setData({ searchName: name }, () => this.searchMovie());
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
        wx.setStorageSync('movieSearchHistory', []);
        wx.showToast({ title: '已清空', icon: 'none' });
      }
    });
  },

  batchSearchMovies() {
    if (!this.data.searchHistory.length) {
      wx.showToast({ title: '暂无可查询的历史记录', icon: 'none' });
      return;
    }
    this.batchQueryMovieDetails(this.data.searchHistory);
  },

  deleteMovie(e) {
    const id = e.currentTarget.dataset.id;
    const name = e.currentTarget.dataset.name;
    wx.showModal({
      title: '删除确认',
      content: '确定删除这部电影吗？',
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        const movieList = this.data.movieList.filter((item) => item.id !== id && item.name !== name);
        this.setData({
          movieList: this.applySelectionState(movieList)
        });
        wx.setStorageSync('movieList', movieList);
        this.updateRowCount();
        wx.showToast({ title: '删除成功', icon: 'none' });
      }
    });
  },

  batchDelete() {
    const { selectedElements, movieList } = this.data;
    if (!selectedElements.length) {
      wx.showToast({ title: '请先选择电影', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '删除确认',
      content: `确定删除已选中的 ${selectedElements.length} 部电影吗？`,
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        const newMovieList = movieList.filter((item) => (
          !selectedElements.includes(item.id) && !selectedElements.includes(item.name)
        ));
        this.setData({
          movieList: this.applySelectionState(newMovieList, []),
          selectedElements: []
        });
        wx.setStorageSync('movieList', newMovieList);
        this.updateRowCount();
        wx.showToast({ title: '删除成功', icon: 'none' });
      }
    });
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
      movieList: this.applySelectionState(this.data.movieList, selectedElements)
    });
  },

  saveToCollection() {
    const { currentMovie } = this.data;
    if (!currentMovie) {
      wx.showToast({ title: '请先搜索电影', icon: 'none' });
      return;
    }

    const movieToSave = this.normalizeMovieItem(currentMovie);
    const movieList = [...this.data.movieList];
    const exists = movieList.some((item) => item.id === movieToSave.id || item.title === movieToSave.title);

    if (exists) {
      wx.showToast({ title: '该电影已收藏', icon: 'none' });
      return;
    }

    movieList.unshift(movieToSave);
    this.setData({
      movieList: this.applySelectionState(movieList)
    });
    this.updateRowCount();
    wx.setStorageSync('movieList', movieList);
    wx.showToast({ title: '收藏成功', icon: 'success' });
  },

  onPullDownRefresh() {
    const movieNames = this.data.movieList.map((item) => item.name || item.title).filter(Boolean);
    if (movieNames.length) {
      this.batchQueryMovieDetails(movieNames);
    }
    wx.stopPullDownRefresh();
  },

  onLoad(options) {
    if (options.name) {
      this.setData({ searchName: options.name }, () => this.searchMovie());
    }

    this.loadFromLocalCache();

    const movieNames = this.data.movieList.map((item) => item.name || item.title).filter(Boolean);
    if (movieNames.length) {
      setTimeout(() => this.batchQueryMovieDetails(movieNames), 300);
    }
  },

  onShow() {
    const hasDataChanged = wx.getStorageSync('movieDataChanged') || false;
    if (hasDataChanged) {
      this.loadFromLocalCache();
      wx.removeStorageSync('movieDataChanged');
    }
  }
});
