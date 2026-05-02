Page({
  data: {
    username: "",
    password: "",
    loading: false,
    bootstrapLoading: true,
    hasAdmin: true,
    error: "",
    statusMessage: ""
  },

  onLoad(options = {}) {
    const presetUsername = String(options.username || "").trim();
    if (presetUsername) {
      this.setData({ username: presetUsername });
    }
  },

  onShow() {
    if (wx.getStorageSync("adminToken")) {
      wx.redirectTo({ url: "/pages/adminDashboard/adminDashboard" });
      return;
    }
    this.fetchBootstrapStatus();
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === "function"
      ? app.getBackendUrl()
      : "http://localhost:5000";
  },

  fetchBootstrapStatus() {
    this.setData({
      bootstrapLoading: true,
      error: "",
      statusMessage: ""
    });

    wx.request({
      url: `${this.getBackendUrl()}/api/admin/bootstrap-status`,
      success: (res) => {
        if (res.data && res.data.code === 0) {
          const hasAdmin = !!res.data.has_admin;
          this.setData({
            bootstrapLoading: false,
            hasAdmin,
            statusMessage: hasAdmin ? "" : "请为你的管理员后台添加账号密码"
          });
          return;
        }

        this.setData({
          bootstrapLoading: false,
          error: (res.data && res.data.error) || "管理员状态获取失败"
        });
      },
      fail: () => {
        this.setData({
          bootstrapLoading: false,
          error: "网络错误，无法连接管理员服务"
        });
      }
    });
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value.trim(), error: "" });
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value, error: "" });
  },

  goToRegister() {
    wx.navigateTo({
      url: "/pages/adminRegister/adminRegister"
    });
  },

  submitLogin() {
    const { username, password, hasAdmin } = this.data;
    if (!hasAdmin) {
      this.goToRegister();
      return;
    }

    if (!username || !password) {
      this.setData({ error: "请输入账号和密码" });
      return;
    }

    this.setData({ loading: true, error: "" });
    wx.request({
      url: `${this.getBackendUrl()}/api/admin/login`,
      method: "POST",
      data: { username, password },
      header: { "Content-Type": "application/json" },
      success: (res) => {
        if (res.data && res.data.code === 0 && res.data.token) {
          wx.setStorageSync("adminToken", res.data.token);
          wx.setStorageSync("adminUsername", res.data.username || username);
          wx.redirectTo({ url: "/pages/adminDashboard/adminDashboard" });
          return;
        }

        this.setData({
          loading: false,
          error: (res.data && res.data.error) || "登录失败"
        });
      },
      fail: () => {
        this.setData({
          loading: false,
          error: "网络错误，登录失败"
        });
      }
    });
  }
});
