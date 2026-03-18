// V2: Account confusion - Instance 3 (variant)
// Subtler pattern: the program checks the account's owner program but not
// its specific key. An attacker can pass any account owned by the Token
// program (e.g., a different token account they control) and pass the check.

use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};

declare_id!("STAKING11111111111111111111111111111111111111");

#[program]
pub mod staking {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, reward_vault: Pubkey) -> Result<()> {
        let state = &mut ctx.accounts.state;
        state.reward_vault = reward_vault;
        state.bump = *ctx.bumps.get("state").unwrap();
        Ok(())
    }

    // BUG: only checks that reward_vault.owner == Token program.
    // Does not verify the specific key equals state.reward_vault.
    // An attacker can pass any SPL token account they own.
    pub fn claim_rewards(ctx: Context<ClaimRewards>, amount: u64) -> Result<()> {
        let reward_vault = &ctx.accounts.reward_vault;

        // Weak check: only verifies Token program ownership, not specific account.
        require!(
            reward_vault.owner == &anchor_spl::token::ID,
            StakingError::InvalidRewardVault
        );

        // Transfer from protocol-controlled vault to user (simplified).
        ctx.accounts.state.total_claimed = ctx.accounts.state.total_claimed.wrapping_add(amount);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + State::SIZE,
        seeds = [b"state"],
        bump
    )]
    pub state: Account<'info, State>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ClaimRewards<'info> {
    #[account(mut, seeds = [b"state"], bump = state.bump)]
    pub state: Account<'info, State>,
    pub user: Signer<'info>,
    // BUG: AccountInfo — only owner checked in instruction body, not key.
    pub reward_vault: AccountInfo<'info>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct State {
    pub reward_vault: Pubkey,
    pub total_claimed: u64,
    pub bump: u8,
}

impl State {
    pub const SIZE: usize = 32 + 8 + 1;
}

#[error_code]
pub enum StakingError {
    #[msg("Invalid reward vault account")]
    InvalidRewardVault,
}
