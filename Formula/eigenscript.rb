class Eigenscript < Formula
  desc "Bytecode VM language with copy-and-patch JIT, observers, and temporal queries"
  homepage "https://github.com/InauguralSystems/EigenScript"
  url "https://github.com/InauguralSystems/EigenScript/archive/refs/tags/v0.43.0.tar.gz"
  sha256 "8654b88c6470f8e842f3b34a198269e486210843faf18196401812aa69708ed6"
  license "MIT"
  head "https://github.com/InauguralSystems/EigenScript.git", branch: "main"

  uses_from_macos "zlib"

  def install
    system "make", "install", "PREFIX=#{prefix}", "CC=#{ENV.cc}"
  end

  test do
    (testpath/"hello.eigs").write <<~EIGS
      print of "hello"
    EIGS
    assert_equal "hello\n", shell_output("#{bin}/eigenscript #{testpath}/hello.eigs")

    # Confirms the runtime found its stdlib at prefix/lib/eigenscript/.
    (testpath/"stdlib.eigs").write <<~EIGS
      import calculus
      print of "stdlib-ok"
    EIGS
    assert_equal "stdlib-ok\n", shell_output("#{bin}/eigenscript #{testpath}/stdlib.eigs")
  end
end
