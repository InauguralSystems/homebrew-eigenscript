class Eigenscript < Formula
  desc "Bytecode VM language with copy-and-patch JIT, observers, and temporal queries"
  homepage "https://github.com/InauguralSystems/EigenScript"
  url "https://github.com/InauguralSystems/EigenScript/archive/refs/tags/v0.20.0.tar.gz"
  sha256 "3750adbcc91892187d314972e6a03e8a2e4eb326aa05e51a9598827f31ff344b"
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
