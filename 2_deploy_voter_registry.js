const VoterRegistry = artifacts.require("VoterRegistry");

module.exports = function(deployer) {
  deployer.deploy(VoterRegistry);
};