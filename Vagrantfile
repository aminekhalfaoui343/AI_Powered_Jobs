Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.box_check_update = false

  nodes = {
    "k8s-master"  => "192.168.56.10",
    "k8s-worker1" => "192.168.56.11",
    "k8s-worker2" => "192.168.56.12",
  }

  nodes.each do |name, ip|
    config.vm.define name do |node|
      node.vm.hostname = name
      node.vm.network "private_network", ip: ip
      node.vm.provider "virtualbox" do |vb|
        vb.name = name
        vb.memory = 2560
        vb.cpus = 2
      end
    end
  end
end