Page({
  data: {
    stats: null,
    loading: true,
    error: ""
  },

  onShow() {
    this.fetchDashboard();
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === "function"
      ? app.getBackendUrl()
      : "http://localhost:5000";
  },

  getAdminHeader() {
    return {
      "Content-Type": "application/json",
      "X-Admin-Token": wx.getStorageSync("adminToken") || ""
    };
  },

  handleUnauthorized() {
    wx.removeStorageSync("adminToken");
    wx.removeStorageSync("adminUsername");
    wx.redirectTo({ url: "/pages/adminLogin/adminLogin" });
  },

  fetchDashboard() {
    this.setData({ loading: true, error: "" });
    wx.request({
      url: `${this.getBackendUrl()}/api/admin/dashboard`,
      header: this.getAdminHeader(),
      success: (res) => {
        if (res.statusCode === 401) {
          this.handleUnauthorized();
          return;
        }

        if (res.data && res.data.code === 0) {
          this.setData({ stats: res.data.data, loading: false });
          return;
        }

        this.setData({
          loading: false,
          error: (res.data && res.data.error) || "加载失败"
        });
      },
      fail: () => {
        this.setData({ loading: false, error: "网络错误，加载失败" });
      }
    });
  },

  goToContent() {
    wx.navigateTo({ url: "/pages/adminContent/adminContent" });
  },

  goToBehavior() {
    wx.navigateTo({ url: "/pages/adminBehavior/adminBehavior?tab=overview" });
  },

  logout() {
    wx.removeStorageSync("adminToken");
    wx.removeStorageSync("adminUsername");
    wx.redirectTo({ url: "/pages/adminLogin/adminLogin" });
  }
});
