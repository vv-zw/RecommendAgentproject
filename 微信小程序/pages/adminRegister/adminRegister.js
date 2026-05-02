Page({
  data: {
    username: "",
    displayName: "",
    password: "",
    confirmPassword: "",
    loading: false,
    error: ""
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === "function"
      ? app.getBackendUrl()
      : "http://localhost:5000";
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value.trim(), error: "" });
  },

  onDisplayNameInput(e) {
    this.setData({ displayName: e.detail.value.trim(), error: "" });
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value, error: "" });
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value, error: "" });
  },

  submitRegister() {
    const { username, displayName, password, confirmPassword } = this.data;

    if (!username) {
      this.setData({ error: "请输入管理员账号" });
      return;
    }
    if (username.length < 3) {
      this.setData({ error: "管理员账号至少 3 位" });
      return;
    }
    if (!password) {
      this.setData({ error: "请输入管理员密码" });
      return;
    }
    if (password.length < 6) {
      this.setData({ error: "密码至少 6 位" });
      return;
    }
    if (password !== confirmPassword) {
      this.setData({ error: "两次输入的密码不一致" });
      return;
    }

    this.setData({ loading: true, error: "" });
    wx.request({
      url: `${this.getBackendUrl()}/api/admin/register`,
      method: "POST",
      data: {
        username,
        password,
        display_name: displayName
      },
      header: { "Content-Type": "application/json" },
      success: (res) => {
        if (res.data && res.data.code === 0) {
          wx.showToast({
            title: "管理员创建成功",
            icon: "success"
          });
          wx.redirectTo({
            url: `/pages/adminLogin/adminLogin?username=${encodeURIComponent(username)}`
          });
          return;
        }

        this.setData({
          loading: false,
          error: (res.data && res.data.error) || "管理员创建失败"
        });
      },
      fail: () => {
        this.setData({
          loading: false,
          error: "网络错误，管理员创建失败"
        });
      }
    });
  }
});
