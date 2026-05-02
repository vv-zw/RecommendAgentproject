Page({
  data: {
    name: "",
    score: 5,
    scoreIndex: 4,
    scores: [1, 2, 3, 4, 5],
    types: ["电影", "剧集", "待看电影", "待看剧集"],
    typeIndex: 0,
    comment: "",
    elements: [
      { label: "古装", selected: false },
      { label: "爱情", selected: false },
      { label: "战争", selected: false },
      { label: "谍战", selected: false },
      { label: "悬疑", selected: false },
      { label: "恐怖", selected: false },
      { label: "家庭", selected: false },
      { label: "搞笑", selected: false },
      { label: "警匪", selected: false },
      { label: "动画", selected: false },
      { label: "剧情", selected: false },
      { label: "纪录片", selected: false },
      { label: "科幻", selected: false },
      { label: "国产剧", selected: false },
      { label: "美剧", selected: false },
      { label: "韩剧", selected: false },
      { label: "热门", selected: false }
    ],
    selectedElements: [],
    saving: false
  },

  noop() {},

  inputName(e) {
    this.setData({ name: e.detail.value.trim() });
  },

  changeType(e) {
    this.setData({ typeIndex: Number(e.detail.value) });
  },

  changeScore(e) {
    const scoreIndex = Number(e.detail.value);
    this.setData({
      scoreIndex,
      score: this.data.scores[scoreIndex]
    });
  },

  inputComment(e) {
    this.setData({ comment: e.detail.value });
  },

  syncSelectedElements(elements) {
    const selectedElements = elements.filter((item) => item.selected).map((item) => item.label);
    this.setData({
      elements,
      selectedElements
    });
  },

  toggleElement(e) {
    const index = Number(e.currentTarget.dataset.index);
    const elements = this.data.elements.map((item, currentIndex) => (
      currentIndex === index ? { ...item, selected: !item.selected } : item
    ));
    this.syncSelectedElements(elements);
  },

  getCategoryKey(type) {
    return {
      "电影": "movieList",
      "剧集": "showList",
      "待看电影": "alreadyList",
      "待看剧集": "alreadyList"
    }[type] || "";
  },

  getContentType(type) {
    return {
      "电影": "movie",
      "剧集": "series",
      "待看电影": "movie",
      "待看剧集": "series"
    }[type] || "";
  },

  isWatchlistType(type) {
    return type === "待看电影" || type === "待看剧集";
  },

  persistToCategoryList(key, item) {
    if (!key) {
      return;
    }

    const list = wx.getStorageSync(key) || [];
    list.push(item);
    wx.setStorageSync(key, list);

    if (key === "showList") {
      wx.setStorageSync("seriesList", list);
    }
  },

  buildNewItem() {
    const { name, score, types, typeIndex, comment, selectedElements } = this.data;
    const selectedType = types[typeIndex];
    const contentType = this.getContentType(selectedType);
    const normalizedGenres = selectedElements.length ? [...selectedElements] : ["未分类"];
    const normalizedComment = String(comment || "").trim() || "暂无短评";

    return {
      id: `custom_${Date.now()}`,
      name,
      title: name,
      score,
      rating: score,
      type: selectedType,
      content_type: contentType,
      comment: normalizedComment,
      genres: normalizedGenres,
      selectedElements: normalizedGenres,
      coverUrl: "",
      cover_url: "",
      year: "",
      director: "",
      actors: "",
      createTime: new Date().toISOString()
    };
  },

  save() {
    const { name, types, typeIndex, saving } = this.data;
    const selectedType = types[typeIndex];

    if (saving) {
      return;
    }

    if (!String(name || "").trim()) {
      wx.showToast({ title: "请输入名称", icon: "none" });
      return;
    }

    const newItem = this.buildNewItem();
    const contentType = this.getContentType(selectedType);
    this.setData({ saving: true });

    try {
      if (this.isWatchlistType(selectedType)) {
        this.saveWatchlistItem(newItem, contentType);
        return;
      }

      const totalList = wx.getStorageSync("totalMovieList") || [];
      totalList.push(newItem);
      wx.setStorageSync("totalMovieList", totalList);

      const categoryKey = this.getCategoryKey(selectedType);
      this.persistToCategoryList(categoryKey, newItem);

      this.resetForm();
      this.syncAfterSave(contentType);
    } catch (error) {
      this.setData({ saving: false });
      console.error("save_failed", error);
      wx.showToast({ title: "保存失败，请重试", icon: "none" });
    }
  },

  saveWatchlistItem(item, contentType) {
    const app = getApp();
    if (!app || typeof app.addWatchlistItem !== "function") {
      this.setData({ saving: false });
      wx.showToast({ title: "当前版本不支持待看同步", icon: "none" });
      return;
    }

    wx.showLoading({ title: "正在保存" });

    app.addWatchlistItem({
      ...item,
      type: contentType,
      content_type: contentType
    }).then(() => {
      this.resetForm();
      return app.syncAndRefresh(contentType, { silent: true }).catch(() => null);
    }).then(() => {
      wx.hideLoading();
      this.setData({ saving: false });
      wx.showToast({ title: "已加入待看清单", icon: "success" });
    }).catch((error) => {
      wx.hideLoading();
      this.setData({ saving: false });
      console.error("save_watchlist_failed", error);
      wx.showToast({ title: "加入待看失败", icon: "none" });
    });
  },

  syncAfterSave(contentType) {
    const app = getApp();
    wx.showLoading({ title: "正在同步" });

    const finish = (title, icon = "success") => {
      wx.hideLoading();
      this.setData({ saving: false });
      wx.showToast({ title, icon });
    };

    const onSuccess = () => {
      finish(contentType ? "已保存并刷新推荐" : "已保存");
    };

    const onFail = () => {
      finish("本地已保存，稍后再同步", "none");
    };

    if (!app || typeof app.syncUserData !== "function") {
      onFail();
      return;
    }

    if (contentType && typeof app.syncAndRefresh === "function") {
      app.syncAndRefresh(contentType, { onSuccess, onFail });
      return;
    }

    app.syncUserData({ onSuccess, onFail });
  },

  resetForm() {
    const resetElements = this.data.elements.map((item) => ({ ...item, selected: false }));
    this.setData({
      name: "",
      score: 5,
      scoreIndex: 4,
      comment: "",
      elements: resetElements,
      selectedElements: []
    });
  },

  goBack() {
    wx.navigateBack();
  }
});
